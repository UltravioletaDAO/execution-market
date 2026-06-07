"""Internal/admin Local Data Collection measurement-uncertainty rubric.

This slice consumes the AAS concept-gap implementation roadmap and expands only
its rank-7 Local Data Collection planning action. It is deliberately not an
operator answer, approval record, answer receipt, customer/worker/public copy,
dataset publication, collection authorization, measurement certification,
analytics/reporting product, route/queue/dispatch surface, or runtime movement.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_concept_gap_implementation_roadmap import (
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS,
    ROADMAP_BLOCKED_CLAIMS,
    load_aas_concept_gap_implementation_roadmap,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_SCHEMA = (
    "city_ops.aas_local_data_collection_measurement_uncertainty_rubric.v1"
)
AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_FILENAME = (
    "aas_local_data_collection_measurement_uncertainty_rubric.json"
)
AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_SAFE_CLAIM = (
    "internal_admin_aas_local_data_collection_measurement_uncertainty_rubric_landed"
)
AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_ID = (
    "execution_market.aas.local_data_collection.measurement_uncertainty_rubric.2026_06_06_2300"
)
AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_STATUS = (
    "internal_admin_planning_only_no_answer_no_approval_no_dataset_publication_or_measurement_certification"
)

FALSE_FLAGS = {
    "rubric_records_operator_answer": False,
    "rubric_records_operator_approval": False,
    "rubric_creates_answer_receipt": False,
    "rubric_selects_future_answer": False,
    "rubric_approves_product_exposure": False,
    "rubric_creates_customer_public_or_worker_copy": False,
    "rubric_authorizes_data_collection_site_access_or_recipient": False,
    "rubric_authorizes_sensor_deployment_survey_or_sampling": False,
    "rubric_certifies_measurement_accuracy_completeness_or_statistical_validity": False,
    "rubric_publishes_dataset_report_dashboard_or_benchmark": False,
    "rubric_creates_public_catalog_pricing_quote_or_route": False,
    "rubric_launches_queue_dispatch_or_worker_instruction": False,
    "rubric_emits_reputation_or_worker_skill_dna": False,
    "rubric_reverifies_payment_or_production": False,
    "rubric_mutates_runtime_acontext_or_irc": False,
    "rubric_exposes_exact_gps_raw_metadata_private_context_or_pii": False,
    "rubric_grants_research_legal_regulatory_or_statistical_authority": False,
    "rubric_publishes_worker_copyable_doctrine": False,
    "rubric_integrates_or_expands_stopped_projects": False,
}

MEASUREMENT_UNCERTAINTY_FIELDS = [
    "measurement_subject_placeholder_without_private_location_or_parties",
    "collection_window_placeholder_without_private_context",
    "measurement_unit_placeholder_with_expected_precision_band",
    "instrument_or_source_type_placeholder_after_redaction_review",
    "sample_count_placeholder_without_dataset_publication",
    "known_missingness_or_coverage_gap_statement",
    "uncertainty_range_or_confidence_caveat_required",
    "photo_screenshot_log_or_text_reference_placeholder_after_redaction_review",
    "unknowns_and_unresolved_measurement_questions",
]

RUBRIC_BOUNDARIES = [
    "record_only_measurement_uncertainty_rubric_not_collection_authorization",
    "separate_observed_value_from_accuracy_completeness_and_statistical_validity",
    "do_not_infer_sensor_calibration_research_validity_or regulatory_acceptance",
    "do_not_publish_dataset_dashboard_benchmark_exact_location_raw_metadata_or_pii",
    "customer_or_worker_copy_requires_separate_explicit_answer_receipt",
]

SAFE_LANGUAGE = [
    "local data collection measurement uncertainty rubric only",
    "dataset publication and measurement certification blocked",
    "observed values require uncertainty and missingness context",
    "collection authorization and statistical authority not claimed",
    "future answer receipt required before dataset delivery or customer use",
]

FORBIDDEN_LANGUAGE = [
    "dataset published",
    "measurement certified",
    "accuracy guaranteed",
    "sample complete",
    "sensor calibrated",
    "statistically valid",
    "regulatory ready",
    "dispatch ready",
]

LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_BLOCKED_CLAIMS = [
    *ROADMAP_BLOCKED_CLAIMS,
    "local_data_collection_measurement_uncertainty_rubric_records_operator_answer",
    "local_data_collection_measurement_uncertainty_rubric_records_operator_approval",
    "local_data_collection_measurement_uncertainty_rubric_creates_answer_receipt",
    "local_data_collection_measurement_uncertainty_rubric_selects_future_answer",
    "local_data_collection_measurement_uncertainty_rubric_treats_planning_as_approval",
    "local_data_collection_measurement_uncertainty_rubric_approves_product_exposure",
    "local_data_collection_measurement_uncertainty_rubric_creates_customer_public_or_worker_copy",
    "local_data_collection_measurement_uncertainty_rubric_authorizes_data_collection_site_access_recipient_or_customer_use",
    "local_data_collection_measurement_uncertainty_rubric_authorizes_sensor_deployment_survey_sampling_or_worker_collection",
    "local_data_collection_measurement_uncertainty_rubric_certifies_measurement_accuracy_completeness_or_statistical_validity",
    "local_data_collection_measurement_uncertainty_rubric_publishes_dataset_report_dashboard_or_benchmark",
    "local_data_collection_measurement_uncertainty_rubric_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "local_data_collection_measurement_uncertainty_rubric_creates_worker_instruction",
    "local_data_collection_measurement_uncertainty_rubric_emits_erc8004_reputation_or_worker_skill_dna",
    "local_data_collection_measurement_uncertainty_rubric_reverifies_payment_or_production",
    "local_data_collection_measurement_uncertainty_rubric_mutates_runtime_acontext_or_irc_session_manager",
    "local_data_collection_measurement_uncertainty_rubric_releases_exact_gps_raw_metadata_private_context_or_pii",
    "local_data_collection_measurement_uncertainty_rubric_grants_research_legal_regulatory_or_statistical_authority",
    "local_data_collection_measurement_uncertainty_rubric_publishes_worker_copyable_doctrine",
    "local_data_collection_measurement_uncertainty_rubric_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "local_data_collection_approved",
    "local_data_collection_customer_ready",
    "data_collection_site_access_authorized",
    "sensor_deployment_authorized",
    "survey_sampling_authorized",
    "dataset_published",
    "dataset_delivery_ready",
    "measurement_certified",
    "accuracy_guaranteed",
    "sample_complete",
    "statistically_valid",
    "regulatory_ready",
    "customer_copy_ready",
    "public_catalog_ready",
    "pricing_ready",
    "queue_ready",
    "dispatch_ready",
    "worker_instruction_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "runtime_parity_proven",
    "live_acontext_ready",
    "gps_release_ready",
    "private_context_release_ready",
    "pii_release_ready",
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


def _local_data_collection_row(roadmap: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in roadmap.get("roadmap_rows", [])
        if row.get("aas_family") == "local_data_collection"
    ]
    if len(rows) != 1:
        raise CityOpsContractError("AAS local data collection rubric source row missing")
    row = rows[0]
    if row.get("planning_sequence_rank") != 7:
        raise CityOpsContractError("AAS local data collection rubric source rank drift")
    if row.get("roadmap_next_planning_slice") != "measurement_uncertainty_rubric_outline_no_dataset_publication":
        raise CityOpsContractError("AAS local data collection rubric source action drift")
    if row.get("still_blocked") is not True:
        raise CityOpsContractError("AAS local data collection rubric source row unblocked")
    if row.get("next_allowed_without_human_answer") != "planning_only_no_fixture_promotion":
        raise CityOpsContractError("AAS local data collection rubric source planning mode drift")
    return row


def _assert_source_roadmap(roadmap: dict[str, Any]) -> None:
    if roadmap.get("schema") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA:
        raise CityOpsContractError("AAS local data collection rubric source schema drift")
    if roadmap.get("roadmap_status") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS:
        raise CityOpsContractError("AAS local data collection rubric source status drift")
    safe = set(roadmap.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS local data collection rubric source safe claim missing")
    blocked = set(roadmap.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(ROADMAP_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS local data collection rubric source missing blocked claims: {sorted(missing)}"
        )
    state = roadmap.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS local data collection rubric source promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS local data collection rubric source selected decision")
    _local_data_collection_row(roadmap)
    firewall = roadmap.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS local data collection rubric source allowed {key}")


def build_aas_local_data_collection_measurement_uncertainty_rubric(
    *,
    artifact_dir: str | Path | None = None,
    source_roadmap: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative Local Data Collection measurement-uncertainty rubric."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    roadmap = source_roadmap or load_aas_concept_gap_implementation_roadmap(
        artifact_dir=source_dir
    )
    _assert_source_roadmap(roadmap)
    row = _local_data_collection_row(roadmap)

    rubric = {
        "schema": AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_SCHEMA,
        "rubric_id": AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_ID,
        "rubric_status": AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_STATUS,
        "source_roadmap": {
            "file": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
            "schema": roadmap["schema"],
            "roadmap_id": roadmap["roadmap_id"],
            "safe_claim": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
            "digest_sha256": _stable_digest(roadmap),
            "consumed_row_family": "local_data_collection",
            "consumed_row_rank": row["planning_sequence_rank"],
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service Local Data Collection planning",
            "stopped_project_firewall": {
                "autojob_work_allowed": False,
                "frontier_academy_work_allowed": False,
                "kk_v2_work_allowed": False,
                "karmacadabra_v2_work_allowed": False,
            },
        },
        "current_operator_state": {
            "explicit_operator_answer_available": False,
            "operator_approval_recorded": False,
            "answer_receipt_created": False,
            "selected_decision": None,
            "recommended_no_human_posture": "planning_only_no_fixture_promotion",
        },
        "readiness": dict(FALSE_FLAGS),
        "local_data_collection_measurement_uncertainty_rubric": {
            "aas_family": "local_data_collection",
            "allowed_use": "internal_admin_measurement_uncertainty_rubric_outline_no_dataset_publication",
            "source_backed_current_state": row["source_backed_current_state"],
            "implementation_concept_expansion": row["implementation_concept_expansion"],
            "roadmap_next_planning_slice": row["roadmap_next_planning_slice"],
            "planning_mode": row["next_allowed_without_human_answer"],
            "measurement_uncertainty_fields": list(MEASUREMENT_UNCERTAINTY_FIELDS),
            "rubric_boundaries": list(RUBRIC_BOUNDARIES),
            "safe_internal_language": list(SAFE_LANGUAGE),
            "forbidden_language": list(FORBIDDEN_LANGUAGE),
            "next_gate_before_any_delivery_or_runtime_movement": "separate_explicit_operator_answer_receipt_then_local_data_collection_customer_or_dispatch_gate",
            "still_blocked": True,
        },
        "sequence_rules": [
            "Treat this rubric as internal/admin planning only, never as approval, collection authorization, or customer copy.",
            "Do not authorize site access, surveys, sensor deployment, sampling, or worker collection from this rubric.",
            "Do not convert observed values into accuracy, completeness, statistical validity, regulatory, benchmark, or dataset publication claims.",
            "Create a separate explicit answer receipt before any Local Data Collection customer, worker, dataset, route, queue, or dispatch gate.",
            "Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.",
        ],
        "claim_boundaries": {
            "safe_to_claim": [
                AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
                AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_BLOCKED_CLAIMS),
        },
        "rubric_digest_sha256": "",
    }
    rubric["rubric_digest_sha256"] = _stable_digest(
        {k: v for k, v in rubric.items() if k != "rubric_digest_sha256"}
    )
    _assert_measurement_uncertainty_rubric_conservative(rubric, source_roadmap=roadmap)
    return rubric


def write_aas_local_data_collection_measurement_uncertainty_rubric(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Local Data Collection measurement-uncertainty rubric."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    rubric = build_aas_local_data_collection_measurement_uncertainty_rubric(
        artifact_dir=base_dir
    )
    path = base_dir / AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_FILENAME
    path.write_text(json.dumps(rubric, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_local_data_collection_measurement_uncertainty_rubric(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Local Data Collection measurement-uncertainty rubric."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    rubric = json.loads(
        (base_dir / AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_roadmap = load_aas_concept_gap_implementation_roadmap(artifact_dir=base_dir)
    _assert_measurement_uncertainty_rubric_conservative(rubric, source_roadmap=source_roadmap)
    return rubric


def _assert_measurement_uncertainty_rubric_conservative(
    rubric: dict[str, Any], *, source_roadmap: dict[str, Any]
) -> None:
    _assert_source_roadmap(source_roadmap)
    if rubric.get("schema") != AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_SCHEMA:
        raise CityOpsContractError("AAS local data collection rubric schema drift")
    if rubric.get("rubric_id") != AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_ID:
        raise CityOpsContractError("AAS local data collection rubric id drift")
    if rubric.get("rubric_status") != AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_STATUS:
        raise CityOpsContractError("AAS local data collection rubric status drift")
    source = rubric.get("source_roadmap", {})
    if source.get("digest_sha256") != _stable_digest(source_roadmap):
        raise CityOpsContractError("AAS local data collection rubric source digest drift")
    if source.get("consumed_row_family") != "local_data_collection" or source.get(
        "consumed_row_rank"
    ) != 7:
        raise CityOpsContractError("AAS local data collection rubric consumed wrong row")

    state = rubric.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(
                f"AAS local data collection rubric operator state promoted {key}"
            )
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS local data collection rubric selected future decision")

    for key, expected in FALSE_FLAGS.items():
        if rubric.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS local data collection rubric readiness promoted {key}")

    fixture = rubric.get("local_data_collection_measurement_uncertainty_rubric", {})
    if fixture.get("aas_family") != "local_data_collection":
        raise CityOpsContractError("AAS local data collection rubric family drift")
    if fixture.get("allowed_use") != "internal_admin_measurement_uncertainty_rubric_outline_no_dataset_publication":
        raise CityOpsContractError("AAS local data collection rubric use drift")
    if fixture.get("planning_mode") != "planning_only_no_fixture_promotion":
        raise CityOpsContractError("AAS local data collection rubric planning mode drift")
    if fixture.get("still_blocked") is not True:
        raise CityOpsContractError("AAS local data collection rubric unblocked")
    if fixture.get("next_gate_before_any_delivery_or_runtime_movement") != (
        "separate_explicit_operator_answer_receipt_then_local_data_collection_customer_or_dispatch_gate"
    ):
        raise CityOpsContractError("AAS local data collection rubric next gate drift")
    if set(MEASUREMENT_UNCERTAINTY_FIELDS) - set(fixture.get("measurement_uncertainty_fields", [])):
        raise CityOpsContractError("AAS local data collection rubric missing measurement uncertainty fields")
    if set(RUBRIC_BOUNDARIES) - set(fixture.get("rubric_boundaries", [])):
        raise CityOpsContractError("AAS local data collection rubric missing boundaries")
    if set(FORBIDDEN_LANGUAGE) - set(fixture.get("forbidden_language", [])):
        raise CityOpsContractError("AAS local data collection rubric missing forbidden language")
    for forbidden in ["dataset published", "measurement certified", "accuracy guaranteed", "dispatch ready"]:
        if forbidden in set(fixture.get("safe_internal_language", [])):
            raise CityOpsContractError("AAS local data collection rubric safe language promoted")

    safe = set(rubric.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(rubric.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS local data collection rubric safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS local data collection rubric forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS local data collection rubric missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"AAS local data collection rubric claim overlap: {sorted(overlap)}"
        )

    firewall = rubric.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS local data collection rubric allowed {key}")
