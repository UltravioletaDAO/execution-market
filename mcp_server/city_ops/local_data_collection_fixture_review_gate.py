"""Local Data Collection adjacent-AAS fixture spec and review gate.

This module stages the next low-authority AAS family from the May 23 packaging
plan: Local Data Collection as a Service. It deliberately stops at an internal
fixture spec and review-gate checklist. It does not create a customer dataset,
publish analytics, authorize a pilot, prove live Acontext/runtime parity,
dispatch work, attach ERC-8004 reputation, expose exact GPS/raw metadata, or
create worker-copyable data-collection doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    READINESS_FALSE_FLAGS,
    REQUIRED_BLOCKED_CLAIMS as TEMPLATE_BLOCKED_CLAIMS,
    REQUIRED_LADDER_STEPS,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_SCHEMA = (
    "city_ops.local_data_collection_fixture_review_gate.v1"
)
LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_FILENAME = (
    "local_data_collection_fixture_review_gate.json"
)
LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_SAFE_CLAIM = (
    "local_data_collection_fixture_review_gate_landed"
)

PACKAGE_FAMILY_ID = "local_data_collection_as_a_service"
OFFER_ID = "one_window_count_or_measurement_snapshot"
SCOPE = "internal_admin_local_data_collection_fixture_spec_and_review_gate_only"
SOURCE_PLAN_DOC = "docs/planning/EXECUTION_MARKET_AAS_NEXT_LOW_AUTHORITY_PACKAGING_PLAN_2026_05_23_10PM.md"

COVERED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "review_gate_checklist",
]
NEXT_REQUIRED_LADDER_STEPS = [
    "reviewed_output_schema",
    "local_reviewed_fixture",
    "internal_package_record",
    "coverage_summary_or_read_only_operator_surface",
    "customer_output_schema_gate",
    "internal_sample_output",
    "explicit_approval_or_hold_decision",
]

REQUIRED_EVIDENCE_FIELDS = [
    "single_place_or_context_reference_without_exact_public_coordinates",
    "single_observation_window",
    "single_count_or_measurement_question",
    "allowed_observation_method",
    "visible_context_photo_or_permitted_visual_snapshot",
    "raw_count_or_measurement_value_with_units_where_applicable",
    "method_note_and_uncertainty_range",
    "ambiguity_or_occlusion_note",
    "what_was_not_checked",
]

REQUIRED_OUTPUT_FIELDS = [
    "task_id_or_local_case_reference",
    "offer_type",
    "plain_language_observation_status",
    "question_answered",
    "observed_value_or_range",
    "unit_or_count_basis",
    "method_summary",
    "observation_window_summary",
    "uncertainty_and_ambiguity_summary",
    "what_was_checked",
    "what_was_not_checked",
    "limitations_and_non_guarantees",
    "recommended_next_action",
    "operator_review_notice",
]

REVIEW_GATE_CHECKS = [
    "source_plan_boundary_matches_local_data_collection_one_place_one_window_one_question",
    "evidence_contract_requires_single_place_single_window_single_measurement_question",
    "method_and_uncertainty_are_required_and_not_treated_as_exactness",
    "observed_value_preserved_without_statistical_representativeness_claim",
    "ambiguity_occlusion_and_what_was_not_checked_are_preserved",
    "privacy_redaction_required_before_any_customer_language",
    "exact_gps_and_raw_metadata_blocked",
    "analytics_prediction_and_official_dataset_claims_blocked",
    "operator_review_required_before_fixture_acceptance",
    "publication_customer_delivery_dispatch_reputation_runtime_and_worker_doctrine_blocked",
]

LOCAL_DATA_COLLECTION_SPECIFIC_BLOCKED_CLAIMS = [
    "statistical_representativeness",
    "continuous_monitoring",
    "official_dataset_certification",
    "exactness_beyond_observed_method",
    "predictive_analytics",
    "public_dataset_ready",
    "worker_copyable_data_collection_doctrine",
]

REQUIRED_BLOCKED_CLAIMS = [
    *TEMPLATE_BLOCKED_CLAIMS,
    *LOCAL_DATA_COLLECTION_SPECIFIC_BLOCKED_CLAIMS,
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "local_data_collection_customer_ready",
    "local_data_collection_catalog_ready",
    "local_data_collection_dataset_ready",
    "local_data_collection_analytics_ready",
    "local_data_collection_dispatch_ready",
    "local_data_collection_reputation_ready",
    "local_data_collection_worker_doctrine_ready",
    "statistically_representative_dataset_ready",
    "measurement_exactness_certified",
}


def build_local_data_collection_fixture_review_gate() -> dict[str, Any]:
    """Build the internal fixture spec and review-gate checklist.

    The returned artifact proves only that the Local Data Collection fixture
    boundary exists. It does not prove reviewed fixtures, customer output,
    dataset publication, analytics, approval, dispatch, reputation, live runtime,
    or worker doctrine.
    """

    gate = {
        "schema": LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_SCHEMA,
        "gate_id": "execution_market.aas.local_data_collection.fixture_review_gate.2026_05_24",
        "scope": SCOPE,
        "package_family_id": PACKAGE_FAMILY_ID,
        "source_plan_doc": SOURCE_PLAN_DOC,
        "source_plan_section": "Rank 2 — Local Data Collection AAS",
        "source_template_safe_claims_inherited": [
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM
        ],
        "safe_to_claim": [
            LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "do_not_claim_yet": _dedupe(REQUIRED_BLOCKED_CLAIMS),
        "ladder_boundary": {
            "required_full_ladder": list(REQUIRED_LADDER_STEPS),
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "fixture_spec": {
            "offer_id": OFFER_ID,
            "offer_label": "One-Window Count / Measurement Snapshot",
            "family_label": "Local Data Collection as a Service",
            "caas_source_pattern": "measurement + proof_observability + site_audit",
            "source_caas_offer": "one_place_one_window_one_count_or_measurement_question",
            "fixture_status": "spec_only_no_reviewed_fixture_yet",
            "operator_review_required": True,
            "customer_copy_changed": False,
            "dataset_created": False,
            "analytics_created": False,
            "phase_1_sellable_claim_allowed": False,
            "automation_claim_allowed": False,
            "required_evidence_fields": list(REQUIRED_EVIDENCE_FIELDS),
            "reviewed_output_schema_draft": {
                "status": "draft_internal_only_not_customer_output_not_dataset",
                "required_fields": list(REQUIRED_OUTPUT_FIELDS),
                "forbidden_fields": [
                    "exact_gps_coordinates",
                    "raw_metadata_blob",
                    "raw_transcript_as_authority",
                    "private_operator_context",
                    "private_subject_identity",
                    "dataset_publication_url",
                    "statistical_representativeness_claim",
                    "continuous_monitoring_claim",
                    "official_dataset_certification_claim",
                    "exactness_beyond_observed_method_claim",
                    "predictive_analytics_claim",
                    "dispatch_instruction_or_assignment",
                    "erc8004_reputation_receipt",
                    "worker_copyable_data_collection_doctrine",
                ],
            },
            "fixture_acceptance_gate": {
                "requires_local_reviewed_fixture": True,
                "requires_privacy_redaction_review": True,
                "requires_method_and_uncertainty_review": True,
                "requires_operator_review_record": True,
                "preserves_safe_and_blocked_claims": True,
                "allows_customer_delivery": False,
                "allows_publication": False,
                "allows_dataset_publication": False,
                "allows_analytics_publication": False,
            },
        },
        "review_gate_checklist": [
            {
                "check_id": check,
                "required": True,
                "status": "pending_future_review",
                "blocks_promotion_until_passed": True,
            }
            for check in REVIEW_GATE_CHECKS
        ],
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "operator_instruction": (
            "Use this only as the Local Data Collection fixture boundary. The next "
            "valid step is a reviewed-output schema plus one local reviewed fixture, "
            "not a customer dataset, analytics product, catalog route, dispatch path, "
            "reputation receipt, live memory claim, or worker-copyable data doctrine."
        ),
        "next_smallest_proof": (
            "Create one synthetic local reviewed fixture for one place, one observation "
            "window, and one count/measurement question that fills this evidence contract "
            "while keeping all promotion and customer/public readiness flags false."
        ),
    }
    _assert_gate_is_conservative(gate)
    return gate


def write_local_data_collection_fixture_review_gate(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Local Data Collection fixture review gate."""

    gate = build_local_data_collection_fixture_review_gate()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_local_data_collection_fixture_review_gate(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Local Data Collection fixture review gate."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        gate = json.load(fh)
    if not isinstance(gate, dict):
        raise CityOpsContractError("Local Data Collection fixture review gate must be a JSON object")
    _assert_gate_is_conservative(gate)
    return gate


def _assert_gate_is_conservative(gate: dict[str, Any]) -> None:
    if gate.get("schema") != LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_SCHEMA:
        raise CityOpsContractError("Local Data Collection fixture review gate schema drift")
    if gate.get("scope") != SCOPE:
        raise CityOpsContractError("Local Data Collection fixture review gate scope drift")
    if gate.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Local Data Collection fixture review gate family drift")
    if gate.get("source_plan_doc") != SOURCE_PLAN_DOC:
        raise CityOpsContractError("Local Data Collection fixture review gate source doc drift")
    if set(gate.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("Local Data Collection fixture review gate has forbidden safe claims")
    missing_blocked = [
        claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in gate.get("do_not_claim_yet", [])
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"Local Data Collection fixture review gate missing blocked claims: {missing_blocked}"
        )
    if gate.get("ladder_boundary", {}).get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Local Data Collection fixture review gate covered steps drift")
    if gate.get("ladder_boundary", {}).get("promotion_allowed") is not False:
        raise CityOpsContractError("Local Data Collection fixture review gate promotion enabled")
    if gate.get("ladder_boundary", {}).get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Local Data Collection fixture review gate next steps drift")

    fixture_spec = gate.get("fixture_spec", {})
    for flag in [
        "customer_copy_changed",
        "dataset_created",
        "analytics_created",
        "phase_1_sellable_claim_allowed",
        "automation_claim_allowed",
    ]:
        if fixture_spec.get(flag) is not False:
            raise CityOpsContractError(
                f"Local Data Collection fixture review gate promoted spec flag {flag}"
            )
    for field in REQUIRED_EVIDENCE_FIELDS:
        if field not in fixture_spec.get("required_evidence_fields", []):
            raise CityOpsContractError(
                f"Local Data Collection fixture review gate missing evidence field {field}"
            )
    schema_draft = fixture_spec.get("reviewed_output_schema_draft", {})
    for field in REQUIRED_OUTPUT_FIELDS:
        if field not in schema_draft.get("required_fields", []):
            raise CityOpsContractError(
                f"Local Data Collection fixture review gate missing output field {field}"
            )
    forbidden_fields = schema_draft.get("forbidden_fields", [])
    for field in [
        "exact_gps_coordinates",
        "raw_metadata_blob",
        "dataset_publication_url",
        "statistical_representativeness_claim",
        "continuous_monitoring_claim",
        "official_dataset_certification_claim",
        "exactness_beyond_observed_method_claim",
        "predictive_analytics_claim",
        "worker_copyable_data_collection_doctrine",
    ]:
        if field not in forbidden_fields:
            raise CityOpsContractError(
                f"Local Data Collection fixture review gate missing forbidden field {field}"
            )
    acceptance_gate = fixture_spec.get("fixture_acceptance_gate", {})
    for flag in [
        "allows_customer_delivery",
        "allows_publication",
        "allows_dataset_publication",
        "allows_analytics_publication",
    ]:
        if acceptance_gate.get(flag) is not False:
            raise CityOpsContractError(
                f"Local Data Collection fixture review gate promoted readiness {flag}"
            )
    if acceptance_gate.get("requires_method_and_uncertainty_review") is not True:
        raise CityOpsContractError(
            "Local Data Collection fixture review gate missing method uncertainty review"
        )

    checklist = gate.get("review_gate_checklist", [])
    if [item.get("check_id") for item in checklist] != REVIEW_GATE_CHECKS:
        raise CityOpsContractError("Local Data Collection fixture review gate checklist drift")
    for item in checklist:
        if item.get("status") != "pending_future_review":
            raise CityOpsContractError(
                "Local Data Collection fixture review gate checklist status drift"
            )
        if item.get("blocks_promotion_until_passed") is not True:
            raise CityOpsContractError(
                "Local Data Collection fixture review gate checklist does not block promotion"
            )
    for flag in READINESS_FALSE_FLAGS:
        if gate.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Local Data Collection fixture review gate promoted readiness {flag}"
            )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
