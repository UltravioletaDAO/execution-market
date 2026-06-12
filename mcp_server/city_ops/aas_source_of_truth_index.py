"""Internal/admin source-of-truth index for City-as-a-Service AAS work.

This proof block consumes the latest two-lane operator-answer schema and marks
which planning docs are current entrypoints versus historical context. It is a
read-only coordination artifact: it records no operator answer, grants no
approval, exposes no customer/worker surface, mutates no runtime, and integrates
no stopped projects.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_two_lane_operator_answer_schema import (
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME,
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SAFE_CLAIM,
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SCHEMA,
    AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_STATUS,
    ANSWER_SCHEMA_BLOCKED_CLAIMS,
    ANSWER_SCHEMA_FALSE_FLAGS,
    DEFAULT_EFFECTIVE_DECISION,
    load_aas_two_lane_operator_answer_schema,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_SOURCE_OF_TRUTH_INDEX_SCHEMA = "city_ops.aas_source_of_truth_index.v1"
AAS_SOURCE_OF_TRUTH_INDEX_FILENAME = "aas_source_of_truth_index.json"
AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM = "internal_admin_aas_source_of_truth_index_landed"
AAS_SOURCE_OF_TRUTH_INDEX_ID = "execution_market.aas.source_of_truth_index.2026_06_03_0200"
AAS_SOURCE_OF_TRUTH_INDEX_STATUS = "read_only_index_no_answer_no_approval"

REPO_ROOT = Path(__file__).resolve().parents[2]
PLANNING_DIR = REPO_ROOT / "docs" / "planning"

CURRENT_ENTRYPOINT_DOCS = [
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md",
        "role": "latest_append_only_execution_board",
        "extension_policy": "current_entrypoint_update_only_when_new_safe_claim_lands",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_00AM_OPERATOR_ANSWER_INTAKE_PACKET_2026_06_12.md",
        "role": "latest_operator_answer_intake_packet",
        "extension_policy": "current_template_only_answer_intake_no_answer_no_approval_no_runtime_delivery_or_stopped_project_movement",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_11PM_DREAM_PRIORITY_OVERRIDE_AND_WORK_SELECTOR_2026_06_11.md",
        "role": "latest_dream_priority_override_work_selector",
        "extension_policy": "current_read_only_kickoff_selector_no_answer_runtime_payment_or_stopped_project_movement",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_06_11.md",
        "role": "latest_final_morning_wrap",
        "extension_policy": "current_read_only_morning_handoff_no_answer_runtime_payment_or_stopped_project_movement",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_11.md",
        "role": "latest_pre_dawn_synthesis_handoff",
        "extension_policy": "current_read_only_daytime_handoff_no_answer_runtime_payment_or_stopped_project_movement",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_4AM_HANDOFF_PACKET_CONTRACT_GUARD_2026_06_11.md",
        "role": "latest_handoff_packet_contract_guard",
        "extension_policy": "current_read_only_packet_contract_guard_no_answer_runtime_payment_or_stopped_project_movement",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_06_07.md",
        "role": "previous_final_morning_wrap_context",
        "extension_policy": "context_only_previous_read_only_morning_handoff_no_answer_runtime_payment_or_stopped_project_movement",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_07.md",
        "role": "latest_pre_dawn_synthesis_handoff",
        "extension_policy": "current_read_only_daytime_handoff_no_answer_runtime_payment_or_stopped_project_movement",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_4AM_EXPONENTIAL_VALUE_CONNECTION_MAP_2026_06_07.md",
        "role": "latest_exponential_value_connection_map",
        "extension_policy": "current_read_only_connection_map_no_answer_runtime_payment_or_stopped_project_movement",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_3AM_SYSTEM_INTEGRATION_STRENGTH_BRIDGE_PACKET_2026_06_07.md",
        "role": "latest_system_integration_strength_bridge_packet",
        "extension_policy": "current_internal_admin_bridge_packet_no_answer_runtime_payment_or_stopped_project_movement",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_2AM_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_2026_06_07.md",
        "role": "latest_no_answer_daytime_operator_prompt_packet",
        "extension_policy": "current_internal_admin_prompt_packet_until_real_operator_answer_exists",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_1AM_RUNTIME_MEMORY_ANSWER_GATE_HOLD_2026_06_07.md",
        "role": "latest_runtime_memory_answer_gate_hold",
        "extension_policy": "current_internal_admin_hold_note_until_explicit_runtime_memory_answer_exists",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_06_06.md",
        "role": "previous_final_morning_wrap_context",
        "extension_policy": "context_only_previous_read_only_morning_handoff_until_real_operator_answer_exists",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_06.md",
        "role": "latest_pre_dawn_synthesis_handoff",
        "extension_policy": "current_read_only_daytime_handoff_until_real_operator_answer_exists",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_10PM_AAS_NEXT_STEPS_2026_06_02.md",
        "role": "latest_next_slice_audit_before_two_lane_schema",
        "extension_policy": "context_only_after_two_lane_operator_answer_schema_landed",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_TWO_LANE_NO_CROSS_PROMOTION_GUARD_IMPLEMENTATION.md",
        "role": "current_two_lane_guard_implementation_note",
        "extension_policy": "source_doc_for_guard_boundaries_only",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_IMPLEMENTATION.md",
        "role": "current_schema_source_until_real_operator_answer_exists",
        "extension_policy": "current_schema_source_until_real_operator_answer_exists",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_SOURCE_OF_TRUTH_INDEX_IMPLEMENTATION.md",
        "role": "source_index_implementation_note",
        "extension_policy": "current_source_index_until_real_operator_answer_exists",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_IMPLEMENTATION.md",
        "role": "latest_safe_decision_support_map_implementation_note",
        "extension_policy": "current_decision_support_map_until_real_operator_answer_exists",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_3AM_SYSTEM_INTEGRATION_DECISION_METER_2026_06_05.md",
        "role": "latest_system_integration_decision_meter",
        "extension_policy": "current_read_only_meter_until_real_operator_answer_exists",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_4AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_2026_06_05.md",
        "role": "latest_pattern_recognition_multiplier_ladder",
        "extension_policy": "current_read_only_pattern_ladder_until_real_operator_answer_exists",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_5AM_PRE_DAWN_SYNTHESIS_HANDOFF_2026_06_05.md",
        "role": "latest_pre_dawn_synthesis_handoff",
        "extension_policy": "current_read_only_daytime_handoff_until_real_operator_answer_exists",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_06_05.md",
        "role": "latest_final_morning_wrap",
        "extension_policy": "current_read_only_morning_handoff_until_real_operator_answer_exists",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_CONCEPT_GAP_MATRIX_2026_06_05.md",
        "role": "latest_source_backed_aas_concept_gap_matrix",
        "extension_policy": "current_internal_admin_planning_matrix_no_answer_or_product_promotion",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_2026_06_05.md",
        "role": "latest_source_backed_aas_concept_gap_implementation_roadmap",
        "extension_policy": "current_internal_admin_planning_sequence_no_answer_or_product_promotion",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_IMPLEMENTATION.md",
        "role": "latest_retail_reality_answer_prerequisite_checklist",
        "extension_policy": "current_internal_admin_prerequisite_checklist_no_answer_or_product_promotion",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_IMPLEMENTATION.md",
        "role": "latest_document_handoff_redaction_delivery_gap_note",
        "extension_policy": "current_internal_admin_maintenance_note_no_answer_or_delivery_promotion",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_IMPLEMENTATION.md",
        "role": "latest_compliance_desk_delivery_path_hold_gap_review",
        "extension_policy": "current_internal_admin_hold_gap_review_no_answer_or_customer_copy_promotion",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_STRENGTH_ROADMAP_CONNECTION_BOARD_IMPLEMENTATION.md",
        "role": "latest_strength_roadmap_connection_board",
        "extension_policy": "current_internal_admin_connection_board_no_answer_or_product_promotion",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_IMPLEMENTATION.md",
        "role": "latest_field_asset_visible_state_fixture_outline",
        "extension_policy": "current_internal_admin_visible_state_outline_no_access_or_dispatch_promotion",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_EVENT_READINESS_OBSERVATION_OUTLINE_IMPLEMENTATION.md",
        "role": "latest_event_readiness_observation_outline",
        "extension_policy": "current_internal_admin_observation_outline_no_permit_security_outcome_or_dispatch_promotion",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_IMPLEMENTATION.md",
        "role": "latest_incident_verification_observation_uncertainty_maintenance",
        "extension_policy": "current_internal_admin_maintenance_no_emergency_official_fault_repair_or_dispatch_promotion",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_IMPLEMENTATION.md",
        "role": "latest_local_data_collection_measurement_uncertainty_rubric",
        "extension_policy": "current_internal_admin_rubric_no_dataset_measurement_certification_or_dispatch_promotion",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_PROPERTY_OPS_BLOCKED_CLAIM_QUARANTINE_VOCABULARY_IMPLEMENTATION.md",
        "role": "latest_property_ops_blocked_claim_quarantine_vocabulary",
        "extension_policy": "current_internal_admin_vocabulary_no_property_access_authority_or_dispatch_promotion",
    },
]

HISTORICAL_CONTEXT_DOCS = [
    {
        "path": "docs/planning/MASTER_PLAN_CITY_AS_A_SERVICE.md",
        "historical_use": "taxonomy_and_background_only",
        "ban": "not_launch_authority_without_fresh_human_answer_and_proof_gate",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_SERVICE_CATALOG.md",
        "historical_use": "service_family_taxonomy_only",
        "ban": "not_public_catalog_or_pricing_authority",
    },
    {
        "path": "docs/planning/EXECUTION_MARKET_AAS_NEXT_CONCEPTS_2026_05_21_10PM.md",
        "historical_use": "older_portfolio_idea_backlog_only",
        "ban": "not_current_next_step_driver",
    },
    {
        "path": "docs/planning/EXECUTION_MARKET_AAS_NEXT_LOW_AUTHORITY_PACKAGING_PLAN_2026_05_23_10PM.md",
        "historical_use": "older_low_authority_packaging_context_only",
        "ban": "not_current_packaging_authority",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_AAS_PRODUCT_FORK_NEXT_GATE_SELECTOR_2026_06_01.md",
        "historical_use": "superseded_product_fork_selector_context_only",
        "ban": "not_product_exposure_approval",
    },
    {
        "path": "docs/planning/CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_06_02.md",
        "historical_use": "sealed_morning_marker_for_june_2_stack_only",
        "ban": "not_latest_answer_schema_authority",
    },
]

STALE_PATTERN_GLOBS = [
    "docs/planning/CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_05_*.md",
    "docs/planning/CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_05_*.md",
    "docs/planning/AAS_SINGLE_BOUNDARY_*.md",
    "docs/planning/CITY_AS_A_SERVICE_SYSTEM_INTEGRATION_FLYWHEEL_*.md",
]

INDEX_FALSE_FLAGS = {
    **ANSWER_SCHEMA_FALSE_FLAGS,
    "source_index_records_operator_answer": False,
    "source_index_records_operator_approval": False,
    "source_index_selects_future_answer": False,
    "source_index_creates_product_exposure": False,
    "source_index_authorizes_runtime_memory_wiring": False,
    "source_index_promotes_historical_docs_to_launch_authority": False,
    "source_index_creates_customer_copy": False,
    "source_index_creates_worker_instruction": False,
    "source_index_creates_dashboard_metric": False,
}

SOURCE_OF_TRUTH_BLOCKED_CLAIMS = [
    *ANSWER_SCHEMA_BLOCKED_CLAIMS,
    "source_of_truth_index_records_operator_answer",
    "source_of_truth_index_records_operator_approval",
    "source_of_truth_index_selects_future_answer",
    "source_of_truth_index_treats_current_entrypoint_as_approval",
    "source_of_truth_index_promotes_master_plan_to_launch_authority",
    "source_of_truth_index_promotes_service_catalog_to_public_catalog",
    "source_of_truth_index_promotes_stale_synthesis_to_current_driver",
    "source_of_truth_index_authorizes_runtime_memory_wiring",
    "source_of_truth_index_authorizes_customer_public_worker_surface",
    "source_of_truth_index_authorizes_catalog_pricing_queue_or_dispatch",
    "source_of_truth_index_emits_erc8004_reputation_or_worker_skill_dna",
    "source_of_truth_index_reverifies_payment_or_production",
    "source_of_truth_index_releases_exact_gps_or_raw_metadata",
    "source_of_truth_index_releases_private_context",
    "source_of_truth_index_grants_domain_authority_claims",
    "source_of_truth_index_publishes_worker_copyable_doctrine",
    "source_of_truth_index_integrates_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(SOURCE_OF_TRUTH_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "retail_reality_approved",
    "product_exposure_approved",
    "runtime_memory_wiring_approved",
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


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _doc_ref(spec: dict[str, str]) -> dict[str, Any]:
    path = REPO_ROOT / spec["path"]
    exists = path.exists()
    ref: dict[str, Any] = {**spec, "exists": exists}
    if exists:
        ref["digest_sha256"] = _file_digest(path)
    else:
        ref["missing_policy"] = "do_not_recreate_from_memory"
    return ref


def _assert_source_schema(schema: dict[str, Any]) -> None:
    if schema.get("schema") != AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SCHEMA:
        raise CityOpsContractError("AAS source index source schema drift")
    if schema.get("schema_status") != AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_STATUS:
        raise CityOpsContractError("AAS source index source schema status drift")
    safe = set(schema.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS source index source safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS source index source schema forbidden safe claims: {sorted(forbidden_safe)}"
        )
    blocked = set(schema.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing_blocked = set(ANSWER_SCHEMA_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS source index source schema missing blocked claims: {sorted(missing_blocked)}"
        )
    current = schema.get("current_values", {})
    if current.get("operator_answer_recorded") is not False:
        raise CityOpsContractError("AAS source index source records operator answer")
    if current.get("operator_approval_recorded") is not False:
        raise CityOpsContractError("AAS source index source records operator approval")
    if current.get("selected_decision") is not None:
        raise CityOpsContractError("AAS source index source selected decision")
    if current.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS source index source effective decision drift")
    readiness = schema.get("readiness", {})
    for key, expected in ANSWER_SCHEMA_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS source index source promoted {key}")


def build_aas_source_of_truth_index(
    *,
    artifact_dir: str | Path | None = None,
    source_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic source-of-truth index for current AAS work."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    answer_schema = source_schema or load_aas_two_lane_operator_answer_schema(
        artifact_dir=source_dir
    )
    _assert_source_schema(answer_schema)

    safe_to_claim = _dedupe(
        [
            *answer_schema["claim_boundaries"]["safe_to_claim"],
            AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *answer_schema["claim_boundaries"]["do_not_claim_yet"],
            *SOURCE_OF_TRUTH_BLOCKED_CLAIMS,
        ]
    )

    index = {
        "schema": AAS_SOURCE_OF_TRUTH_INDEX_SCHEMA,
        "index_id": AAS_SOURCE_OF_TRUTH_INDEX_ID,
        "scope": "internal_admin_aas_planning_source_of_truth_index_only",
        "index_status": AAS_SOURCE_OF_TRUTH_INDEX_STATUS,
        "source_policy": "consume_latest_two_lane_operator_answer_schema_only",
        "source_schema": {
            "file": AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME,
            "schema": answer_schema["schema"],
            "schema_id": answer_schema["schema_id"],
            "safe_claim": AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_SAFE_CLAIM,
            "digest_sha256": _stable_digest(answer_schema),
            "schema_status": answer_schema["schema_status"],
            "effective_decision": answer_schema["current_values"]["effective_decision"],
        },
        "current_entrypoints": [_doc_ref(spec) for spec in CURRENT_ENTRYPOINT_DOCS],
        "historical_context_only": [_doc_ref(spec) for spec in HISTORICAL_CONTEXT_DOCS],
        "stale_pattern_extension_ban_list": [
            {
                "glob": pattern,
                "allowed_use": "historical_context_only",
                "ban": "do_not_extend_as_active_next_step_source_without_new_human_answer_and_proof_gate",
            }
            for pattern in STALE_PATTERN_GLOBS
        ],
        "current_no_answer_posture": {
            "operator_answer_recorded": False,
            "operator_approval_recorded": False,
            "selected_decision": None,
            "effective_decision": DEFAULT_EFFECTIVE_DECISION,
            "safe_next_move_without_human_answer": (
                "hold_or_append_read_only_final_wrap_handoff; do not add product, runtime, "
                "dispatch, reputation, payment, location, private-context, authority, or stopped-project claims"
            ),
        },
        "readiness": {
            "internal_admin_source_index_landed": True,
            "source_schema_verified": True,
            "current_entrypoints_indexed": True,
            "historical_docs_demoted_to_context_only": True,
            "stale_extension_ban_list_present": True,
            "default_off_non_authorizing": True,
            **INDEX_FALSE_FLAGS,
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
            "first_read": "DREAM-PRIORITIES.md",
            "then_read": "docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md",
            "if_no_real_answer": "stop_at_hold_or_read_only_final_wrap",
            "if_real_answer_exists": (
                "create a separate answer record against aas_two_lane_operator_answer_schema.json"
            ),
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "not_dashboard_spec": True,
        },
        "index_verdict": (
            "source_of_truth_index_landed_no_answer_no_approval_current_entrypoints_marked_"
            "historical_docs_demoted_no_runtime_product_reputation_payment_dispatch_or_stopped_project_promotion"
        ),
    }
    _assert_aas_source_of_truth_index(index, source_schema=answer_schema)
    return index


def _assert_aas_source_of_truth_index(
    index: dict[str, Any], *, source_schema: dict[str, Any]
) -> None:
    _assert_source_schema(source_schema)
    if index.get("schema") != AAS_SOURCE_OF_TRUTH_INDEX_SCHEMA:
        raise CityOpsContractError("AAS source index schema drift")
    if index.get("index_id") != AAS_SOURCE_OF_TRUTH_INDEX_ID:
        raise CityOpsContractError("AAS source index id drift")
    if index.get("index_status") != AAS_SOURCE_OF_TRUTH_INDEX_STATUS:
        raise CityOpsContractError("AAS source index status drift")
    source = index.get("source_schema", {})
    if source.get("file") != AAS_TWO_LANE_OPERATOR_ANSWER_SCHEMA_FILENAME:
        raise CityOpsContractError("AAS source index source file drift")
    if source.get("digest_sha256") != _stable_digest(source_schema):
        raise CityOpsContractError("AAS source index source digest drift")
    if source.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS source index source effective decision drift")

    current_paths = [item.get("path") for item in index.get("current_entrypoints", [])]
    expected_current = [item["path"] for item in CURRENT_ENTRYPOINT_DOCS]
    if current_paths != expected_current:
        raise CityOpsContractError("AAS source index current entrypoints drift")
    for item in index.get("current_entrypoints", []):
        if item.get("exists") is not True:
            raise CityOpsContractError(f"AAS source index current entrypoint missing: {item}")
        if "digest_sha256" not in item:
            raise CityOpsContractError("AAS source index current entrypoint missing digest")
        policy = item.get("extension_policy", "")
        if not policy or "launch" in policy or "public" in policy:
            raise CityOpsContractError("AAS source index current entrypoint policy drift")

    historical_paths = [item.get("path") for item in index.get("historical_context_only", [])]
    expected_historical = [item["path"] for item in HISTORICAL_CONTEXT_DOCS]
    if historical_paths != expected_historical:
        raise CityOpsContractError("AAS source index historical docs drift")
    for item in index.get("historical_context_only", []):
        if item.get("historical_use") is None or item.get("ban") is None:
            raise CityOpsContractError("AAS source index historical doc missing use or ban")
        ban = item.get("ban", "")
        if "not_" not in ban and "not " not in ban:
            raise CityOpsContractError("AAS source index historical doc ban drift")

    bans = index.get("stale_pattern_extension_ban_list", [])
    if [item.get("glob") for item in bans] != STALE_PATTERN_GLOBS:
        raise CityOpsContractError("AAS source index stale glob drift")
    for item in bans:
        if item.get("allowed_use") != "historical_context_only":
            raise CityOpsContractError("AAS source index stale pattern promoted")

    posture = index.get("current_no_answer_posture", {})
    if posture.get("operator_answer_recorded") is not False:
        raise CityOpsContractError("AAS source index recorded operator answer")
    if posture.get("operator_approval_recorded") is not False:
        raise CityOpsContractError("AAS source index recorded operator approval")
    if posture.get("selected_decision") is not None:
        raise CityOpsContractError("AAS source index selected a decision")
    if posture.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS source index effective decision drift")

    readiness = index.get("readiness", {})
    for key, expected in INDEX_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS source index promoted readiness {key}")

    safe = set(index.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(index.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS source index safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS source index forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(SOURCE_OF_TRUTH_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS source index missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(f"AAS source index claim overlap: {sorted(overlap)}")
    if index.get("still_blocked_claims") != index.get("claim_boundaries", {}).get(
        "do_not_claim_yet"
    ):
        raise CityOpsContractError("AAS source index blocked claims drift")

    firewall = index.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS source index allowed {key}")


def write_aas_source_of_truth_index(*, artifact_dir: str | Path | None = None) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    index = build_aas_source_of_truth_index(artifact_dir=target_dir)
    target_path = target_dir / AAS_SOURCE_OF_TRUTH_INDEX_FILENAME
    target_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path


def load_aas_source_of_truth_index(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_SOURCE_OF_TRUTH_INDEX_FILENAME
    index = json.loads(path.read_text(encoding="utf-8"))
    source_schema = load_aas_two_lane_operator_answer_schema(artifact_dir=source_dir)
    _assert_aas_source_of_truth_index(index, source_schema=source_schema)
    return index
