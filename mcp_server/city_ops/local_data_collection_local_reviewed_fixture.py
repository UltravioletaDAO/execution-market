"""Local Data Collection adjacent-AAS local reviewed fixture.

This module advances Local Data Collection as a Service by exactly one safe rung
after the fixture/review gate: one synthetic reviewed fixture for one place, one
observation window, and one count/measurement question. It remains
internal/admin only. It does not create a customer dataset, publish analytics,
authorize a catalog route, dispatch work, attach ERC-8004 reputation, prove live
Acontext/runtime parity, expose exact GPS/raw metadata, or create
worker-copyable data-collection doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    READINESS_FALSE_FLAGS,
)
from .contracts import CityOpsContractError
from .local_data_collection_fixture_review_gate import (
    LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_FILENAME,
    LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_BLOCKED_CLAIMS as GATE_BLOCKED_CLAIMS,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
    LOCAL_DATA_COLLECTION_SPECIFIC_BLOCKED_CLAIMS,
    load_local_data_collection_fixture_review_gate,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR

LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_SCHEMA = (
    "city_ops.local_data_collection_local_reviewed_fixture.v1"
)
LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_FILENAME = (
    "local_data_collection_local_reviewed_fixture.json"
)
LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM = (
    "local_data_collection_local_reviewed_fixture_landed"
)

FIXTURE_ID = "execution_market.aas.local_data_collection.local_reviewed_fixture.001"
SCOPE = "internal_admin_local_data_collection_local_reviewed_fixture_only"

COVERED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "review_gate_checklist",
    "reviewed_output_schema",
    "local_reviewed_fixture",
]
NEXT_REQUIRED_LADDER_STEPS = [
    "internal_package_record",
    "coverage_summary_or_read_only_operator_surface",
    "customer_output_schema_gate",
    "internal_sample_output",
    "explicit_approval_or_hold_decision",
]

LOCAL_FIXTURE_REVIEW_CHECKS = [
    "source_gate_safe_claims_present",
    "all_required_local_data_evidence_fields_populated",
    "reviewed_output_uses_only_allowed_fields",
    "one_place_one_window_one_question_boundary_preserved",
    "observed_value_preserved_as_method_bounded_not_exact_or_representative",
    "uncertainty_range_and_ambiguity_note_preserved",
    "privacy_redaction_completed_for_local_fixture",
    "exact_gps_raw_metadata_private_identity_and_raw_context_absent",
    "dataset_analytics_prediction_and_official_certification_claims_absent",
    "non_representativeness_and_non_monitoring_language_present",
    "customer_public_dispatch_reputation_runtime_and_worker_doctrine_still_blocked",
]

ADDITIONAL_BLOCKED_CLAIMS = [
    "local_data_collection_local_fixture_customer_delivery_ready",
    "local_data_collection_local_fixture_publication_ready",
    "local_data_collection_local_fixture_catalog_ready",
    "local_data_collection_local_fixture_dataset_ready",
    "local_data_collection_local_fixture_analytics_ready",
    "local_data_collection_local_fixture_pricing_ready",
    "local_data_collection_local_fixture_dispatch_ready",
    "local_data_collection_local_fixture_reputation_ready",
    "local_data_collection_local_fixture_live_acontext_ready",
    "local_data_collection_local_fixture_worker_skill_dna_ready",
    "local_data_collection_local_fixture_worker_doctrine_ready",
    "local_data_collection_local_fixture_statistical_representativeness_ready",
    "local_data_collection_local_fixture_continuous_monitoring_ready",
    "local_data_collection_local_fixture_official_dataset_certification_ready",
    "local_data_collection_local_fixture_predictive_analytics_ready",
    "local_data_collection_local_fixture_exactness_certification_ready",
]

FORBIDDEN_SAFE_CLAIMS = (
    set(GATE_BLOCKED_CLAIMS)
    | set(LOCAL_DATA_COLLECTION_SPECIFIC_BLOCKED_CLAIMS)
    | set(ADDITIONAL_BLOCKED_CLAIMS)
    | {
        "customer_dataset_ready",
        "public_dataset_ready",
        "analytics_ready",
        "statistically_representative_dataset_ready",
        "continuous_monitoring_ready",
        "official_dataset_certification_ready",
        "predictive_analytics_ready",
        "measurement_exactness_certified",
        "worker_copyable_data_collection_doctrine_ready",
    }
)

FORBIDDEN_PAYLOAD_KEYS = {
    "exact_gps_coordinates",
    "gps_coordinates",
    "latitude",
    "longitude",
    "raw_metadata_blob",
    "raw_transcript_as_authority",
    "private_operator_context",
    "private_subject_identity",
    "dataset_publication_url",
    "dispatch_instruction_or_assignment",
    "erc8004_reputation_receipt",
    "worker_copyable_data_collection_doctrine",
}


def build_local_data_collection_local_reviewed_fixture(
    *, gate: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build one internal reviewed fixture for Local Data Collection.

    The fixture is synthetic and non-site-specific. It proves only that the
    local review shape can carry one bounded count/measurement observation with
    method and uncertainty preserved. It does not prove customer/public output,
    dataset publication, analytics, statistical representativeness, continuous
    monitoring, exactness certification, dispatch, reputation, live runtime, or
    worker-copyable doctrine.
    """

    source_gate = gate or load_local_data_collection_fixture_review_gate()
    _assert_source_gate(source_gate)

    reviewed_output = {
        "task_id_or_local_case_reference": "local_data_collection_fixture_001",
        "offer_type": OFFER_ID,
        "plain_language_observation_status": (
            "A bounded one-window count/measurement observation was reviewed for a "
            "synthetic local fixture. The output records the question, observed "
            "value, method, uncertainty, and exclusions. It is not a representative "
            "dataset, not continuous monitoring, not official certification, not "
            "predictive analytics, and not exact beyond the reviewed method."
        ),
        "question_answered": (
            "How many visible queue positions were occupied during one synthetic "
            "observation window?"
        ),
        "observed_value_or_range": "observed_count_range_7_to_9_visible_positions",
        "unit_or_count_basis": "visible_positions_counted_by_redacted_synthetic_snapshot_review",
        "method_summary": (
            "Manual visual count from a redacted synthetic context snapshot. The "
            "review preserves a +/-1 uncertainty range because one edge case was "
            "partially occluded."
        ),
        "observation_window_summary": (
            "Single synthetic observation window only; no exact timestamp, GPS, "
            "address, route trace, raw metadata, or private subject identity is included."
        ),
        "uncertainty_and_ambiguity_summary": (
            "Count is expressed as a range because one visible item was ambiguous. "
            "The fixture does not infer averages, trends, future conditions, or "
            "population-level representativeness."
        ),
        "what_was_checked": [
            "one_synthetic_place_or_context_reference_without_exact_coordinates",
            "one_observation_window",
            "one_visible_count_question",
            "redacted_visual_snapshot_source_type",
            "method_note_and_uncertainty_range",
            "ambiguity_or_occlusion_note",
            "absence_of_exact_gps_raw_metadata_private_identity_dataset_publication_and_dispatch_fields",
        ],
        "what_was_not_checked": [
            "statistical_representativeness",
            "continuous_monitoring",
            "official_dataset_certification",
            "exactness_beyond_reviewed_method",
            "predictive_analytics",
            "future_conditions_or_trends",
            "customer_delivery_readiness",
            "dispatch_readiness",
            "erc8004_reputation_readiness",
            "worker_copyable_data_collection_doctrine",
        ],
        "limitations_and_non_guarantees": [
            "This fixture is synthetic and local; it does not represent a real location or customer case.",
            "The reviewed observation covers one place/context, one window, and one count question only.",
            "The value is method-bounded and includes an uncertainty range; it is not certified exactness.",
            "No statistical representativeness, continuous monitoring, official dataset status, predictive analytics, or future-state claim is made.",
            "No customer dataset, publication, catalog route, pricing quote, dispatch path, reputation receipt, live runtime proof, or worker doctrine is authorized.",
        ],
        "recommended_next_action": (
            "Create a Local Data Collection internal package record that consumes "
            "this reviewed fixture while keeping all customer/public/dataset/analytics/"
            "pricing/dispatch/reputation/runtime/GPS/worker-doctrine readiness false."
        ),
        "operator_review_notice": (
            "Reviewed for local fixture shape only. Keep customer/public/catalog/"
            "dataset/analytics/pricing/dispatch/reputation/live-runtime/exactness/"
            "representativeness/continuous-monitoring/worker-doctrine readiness false."
        ),
    }

    fixture = {
        "schema": LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_SCHEMA,
        "fixture_id": FIXTURE_ID,
        "scope": SCOPE,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_gate_id": source_gate["gate_id"],
        "source_gate_schema": source_gate["schema"],
        "source_safe_claims_inherited": [
            LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "safe_to_claim": [
            LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
            LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "do_not_claim_yet": _dedupe(
            [
                *GATE_BLOCKED_CLAIMS,
                *source_gate.get("do_not_claim_yet", []),
                *ADDITIONAL_BLOCKED_CLAIMS,
            ]
        ),
        "ladder_boundary": {
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "local_fixture": {
            "review_status": "reviewed_internal_fixture_only_not_promoted",
            "fixture_kind": "synthetic_one_window_count_measurement_snapshot",
            "customer_copy_changed": False,
            "customer_delivery_allowed": False,
            "publication_allowed": False,
            "catalog_allowed": False,
            "dataset_publication_allowed": False,
            "analytics_publication_allowed": False,
            "pricing_quote_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "live_runtime_write_allowed": False,
            "worker_skill_dna_allowed": False,
            "worker_copyable_doctrine_allowed": False,
            "statistical_representativeness_claim_allowed": False,
            "continuous_monitoring_claim_allowed": False,
            "official_dataset_certification_allowed": False,
            "exactness_beyond_method_allowed": False,
            "predictive_analytics_allowed": False,
            "evidence_contract_snapshot": {
                "single_place_or_context_reference_without_exact_public_coordinates": (
                    "redacted_synthetic_local_context_reference_no_exact_public_coordinates"
                ),
                "single_observation_window": (
                    "relative_synthetic_window_no_exact_timestamp_address_route_trace_or_raw_metadata"
                ),
                "single_count_or_measurement_question": (
                    "visible_queue_position_count_inside_one_window"
                ),
                "allowed_observation_method": (
                    "manual_visual_count_from_permitted_redacted_synthetic_snapshot"
                ),
                "visible_context_photo_or_permitted_visual_snapshot": (
                    "redacted_synthetic_visual_snapshot_source_type_only"
                ),
                "raw_count_or_measurement_value_with_units_where_applicable": (
                    "count_range_7_to_9_visible_positions"
                ),
                "method_note_and_uncertainty_range": (
                    "manual_count_with_plus_minus_one_uncertainty_due_to_partial_occlusion"
                ),
                "ambiguity_or_occlusion_note": (
                    "one edge case partially occluded; output remains a range not an exact certified count"
                ),
                "what_was_not_checked": (
                    "representativeness_continuous_monitoring_official_dataset_predictive_analytics_future_state"
                ),
            },
            "reviewed_output_schema": {
                "status": "local_reviewed_fixture_internal_only_not_customer_output_not_dataset",
                "required_fields": list(REQUIRED_OUTPUT_FIELDS),
                "forbidden_fields": list(
                    source_gate["fixture_spec"]["reviewed_output_schema_draft"][
                        "forbidden_fields"
                    ]
                ),
            },
            "reviewed_output": reviewed_output,
        },
        "local_review_checks": [
            {
                "check_id": check,
                "status": "passed_for_local_fixture_only",
                "blocks_promotion_until_later_gate": True,
            }
            for check in LOCAL_FIXTURE_REVIEW_CHECKS
        ],
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "operator_instruction": (
            "Use this only as the Local Data Collection local reviewed fixture. "
            "The next valid step is an internal package record; do not convert it "
            "into a customer dataset, analytics product, catalog listing, pricing "
            "quote, dispatch path, reputation receipt, live memory proof, or "
            "worker-copyable data-collection doctrine."
        ),
        "next_smallest_proof": (
            "Create a Local Data Collection internal package record that consumes "
            "this local fixture, summarizes evidence coverage, and preserves all "
            "customer/public/dataset/analytics/pricing/dispatch/reputation/runtime/"
            "GPS/exactness/worker-doctrine blocks."
        ),
    }
    _assert_fixture_is_conservative(fixture, source_gate)
    return fixture


def write_local_data_collection_local_reviewed_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Local Data Collection local reviewed fixture."""

    fixture = build_local_data_collection_local_reviewed_fixture()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_FILENAME
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_local_data_collection_local_reviewed_fixture(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Local Data Collection fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        fixture = json.load(fh)
    if not isinstance(fixture, dict):
        raise CityOpsContractError("Local Data Collection local reviewed fixture must be a JSON object")
    if (source_dir / LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_FILENAME).exists():
        gate = load_local_data_collection_fixture_review_gate(artifact_dir=source_dir)
    else:
        gate = load_local_data_collection_fixture_review_gate()
    _assert_fixture_is_conservative(fixture, gate)
    return fixture


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_SAFE_CLAIM not in gate.get("safe_to_claim", []):
        raise CityOpsContractError("Local Data Collection local fixture source safe claim missing")
    if gate.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Local Data Collection local fixture source family drift")
    if gate.get("fixture_spec", {}).get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Local Data Collection local fixture source offer drift")
    if gate.get("ladder_boundary", {}).get("promotion_allowed") is not False:
        raise CityOpsContractError("Local Data Collection local fixture source gate promoted readiness")
    if gate.get("fixture_spec", {}).get("dataset_created") is not False:
        raise CityOpsContractError("Local Data Collection local fixture source gate promoted dataset")
    if gate.get("fixture_spec", {}).get("analytics_created") is not False:
        raise CityOpsContractError("Local Data Collection local fixture source gate promoted analytics")
    for field in REQUIRED_EVIDENCE_FIELDS:
        if field not in gate.get("fixture_spec", {}).get("required_evidence_fields", []):
            raise CityOpsContractError(
                f"Local Data Collection local fixture source missing evidence field {field}"
            )
    for field in REQUIRED_OUTPUT_FIELDS:
        if field not in gate.get("fixture_spec", {}).get("reviewed_output_schema_draft", {}).get(
            "required_fields", []
        ):
            raise CityOpsContractError(
                f"Local Data Collection local fixture source missing output field {field}"
            )


def _assert_fixture_is_conservative(fixture: dict[str, Any], gate: dict[str, Any]) -> None:
    _assert_source_gate(gate)
    if fixture.get("schema") != LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_SCHEMA:
        raise CityOpsContractError("Local Data Collection local reviewed fixture schema drift")
    if fixture.get("scope") != SCOPE:
        raise CityOpsContractError("Local Data Collection local reviewed fixture scope drift")
    if fixture.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Local Data Collection local reviewed fixture family drift")
    if fixture.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Local Data Collection local reviewed fixture offer drift")
    if set(fixture.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("Local Data Collection local reviewed fixture has forbidden safe claims")
    missing_blocked = [
        claim
        for claim in [*GATE_BLOCKED_CLAIMS, *ADDITIONAL_BLOCKED_CLAIMS]
        if claim not in fixture.get("do_not_claim_yet", [])
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"Local Data Collection local reviewed fixture missing blocked claims: {missing_blocked}"
        )
    if fixture.get("ladder_boundary", {}).get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Local Data Collection local reviewed fixture covered steps drift")
    if fixture.get("ladder_boundary", {}).get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Local Data Collection local reviewed fixture next steps drift")
    if fixture.get("ladder_boundary", {}).get("promotion_allowed") is not False:
        raise CityOpsContractError("Local Data Collection local reviewed fixture promotion enabled")

    local_fixture = fixture.get("local_fixture", {})
    for flag in [
        "customer_copy_changed",
        "customer_delivery_allowed",
        "publication_allowed",
        "catalog_allowed",
        "dataset_publication_allowed",
        "analytics_publication_allowed",
        "pricing_quote_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "live_runtime_write_allowed",
        "worker_skill_dna_allowed",
        "worker_copyable_doctrine_allowed",
        "statistical_representativeness_claim_allowed",
        "continuous_monitoring_claim_allowed",
        "official_dataset_certification_allowed",
        "exactness_beyond_method_allowed",
        "predictive_analytics_allowed",
    ]:
        if local_fixture.get(flag) is not False:
            raise CityOpsContractError(
                f"Local Data Collection local reviewed fixture promoted fixture flag {flag}"
            )

    evidence = local_fixture.get("evidence_contract_snapshot", {})
    for field in REQUIRED_EVIDENCE_FIELDS:
        if field not in evidence:
            raise CityOpsContractError(
                f"Local Data Collection local reviewed fixture missing evidence field {field}"
            )
    reviewed_output = local_fixture.get("reviewed_output", {})
    for field in REQUIRED_OUTPUT_FIELDS:
        if field not in reviewed_output:
            raise CityOpsContractError(
                f"Local Data Collection local reviewed fixture missing reviewed output field {field}"
            )
    schema = local_fixture.get("reviewed_output_schema", {})
    if schema.get("status") != "local_reviewed_fixture_internal_only_not_customer_output_not_dataset":
        raise CityOpsContractError("Local Data Collection local reviewed fixture schema status drift")
    for field in REQUIRED_OUTPUT_FIELDS:
        if field not in schema.get("required_fields", []):
            raise CityOpsContractError(
                f"Local Data Collection local reviewed fixture schema missing field {field}"
            )
    for forbidden_key in FORBIDDEN_PAYLOAD_KEYS:
        if _contains_key(fixture, forbidden_key):
            raise CityOpsContractError(
                f"Local Data Collection local reviewed fixture leaked forbidden payload key {forbidden_key}"
            )
    for fragment in [
        "statistically representative",
        "continuous monitoring is provided",
        "official dataset certification",
        "predictive analytics are provided",
        "certified exactness provided",
        "customer dataset is ready",
        "dispatch instruction",
        "reputation receipt attached",
        "worker-copyable doctrine",
    ]:
        if fragment in json.dumps(reviewed_output, sort_keys=True).lower():
            raise CityOpsContractError(
                "Local Data Collection local reviewed fixture overclaimed dataset or analytics readiness"
            )
    checks = fixture.get("local_review_checks", [])
    if [item.get("check_id") for item in checks] != LOCAL_FIXTURE_REVIEW_CHECKS:
        raise CityOpsContractError("Local Data Collection local reviewed fixture review checks drift")
    for item in checks:
        if item.get("status") != "passed_for_local_fixture_only":
            raise CityOpsContractError("Local Data Collection local reviewed fixture check status drift")
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError(
                "Local Data Collection local reviewed fixture review check stopped blocking promotion"
            )
    for flag in READINESS_FALSE_FLAGS:
        if fixture.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Local Data Collection local reviewed fixture promoted readiness {flag}"
            )


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
