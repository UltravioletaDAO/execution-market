"""Incident Verification adjacent-AAS internal package record.

This module advances Incident Verification by exactly one rung: from a local
reviewed fixture to an internal package record. It remains internal/admin only.
It does not create customer copy, publish a catalog, authorize a pilot, prove
live Acontext/runtime parity, dispatch work, attach ERC-8004 reputation, expose
exact GPS/raw metadata, create emergency or safety certification claims,
diagnose or complete repairs, adjust insurance, claim SLA uptime, create
official incident reports, or create worker-copyable incident doctrine.
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
from .incident_verification_fixture_review_gate import (
    ARTIFACT_DIR,
    INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
)
from .incident_verification_local_reviewed_fixture import (
    FIXTURE_ID,
    INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME,
    INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
    load_incident_verification_local_reviewed_fixture,
)

INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SCHEMA = (
    "city_ops.incident_verification_internal_package_record.v1"
)
INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME = (
    "incident_verification_internal_package_record.json"
)
INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM = (
    "incident_verification_internal_package_record_landed"
)

PACKAGE_ID = "execution_market.aas.incident_verification.internal_package_record.001"
SCOPE = "internal_admin_incident_verification_package_record_only"
PACKAGE_STATUS = "internal_package_record_only_not_customer_ready"

COVERED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "review_gate_checklist",
    "reviewed_output_schema",
    "local_reviewed_fixture",
    "internal_package_record",
]
NEXT_REQUIRED_LADDER_STEPS = [
    "coverage_summary_or_read_only_operator_surface",
    "customer_output_schema_gate",
    "internal_sample_output",
    "explicit_approval_or_hold_decision",
]

PACKAGE_REVIEW_CHECKS = [
    "source_local_fixture_safe_claims_present",
    "source_fixture_review_status_internal_only",
    "package_uses_only_local_reviewed_fixture_artifact",
    "incident_evidence_and_reviewed_output_fields_preserved",
    "incident_question_remains_observational_and_bounded",
    "place_time_window_preserves_no_exact_public_coordinates",
    "wide_and_close_evidence_remain_permitted_summaries_only",
    "severity_taxonomy_remains_observational_not_safety_certification",
    "uncertainty_and_what_was_not_checked_remain_explicit",
    "follow_on_trigger_remains_operator_next_step_only_not_dispatch",
    "emergency_safety_repair_insurance_sla_and_official_report_claims_absent",
    "customer_public_dispatch_reputation_and_worker_doctrine_still_blocked",
    "next_ladder_steps_require_separate_artifacts",
]

ADDITIONAL_BLOCKED_CLAIMS = [
    "incident_verification_internal_package_customer_delivery_ready",
    "incident_verification_internal_package_publication_ready",
    "incident_verification_internal_package_catalog_ready",
    "incident_verification_internal_package_dispatch_ready",
    "incident_verification_internal_package_reputation_ready",
    "incident_verification_internal_package_worker_doctrine_ready",
    "incident_verification_internal_package_live_acontext_ready",
    "incident_verification_internal_package_approval_ready",
    "incident_verification_internal_package_emergency_ready",
    "incident_verification_internal_package_safety_certification_ready",
    "incident_verification_internal_package_repair_ready",
    "incident_verification_internal_package_insurance_ready",
    "incident_verification_internal_package_official_report_ready",
    "incident_verification_internal_package_sla_ready",
    "incident_verification_customer_ready",
    "incident_verification_catalog_ready",
    "incident_verification_dispatch_ready",
    "incident_verification_reputation_ready",
    "incident_verification_worker_doctrine_ready",
    "incident_verification_official_report_ready",
    "incident_verification_safety_ready",
    "incident_verification_repair_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(ADDITIONAL_BLOCKED_CLAIMS) | {
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_ready",
    "operator_publish_approval",
    "customer_delivery_approval",
    "publication_approved",
    "emergency_response",
    "safety_certification",
    "repair_diagnosis",
    "repair_completion",
    "repair_diagnosis_or_completion",
    "insurance_adjustment",
    "sla_uptime",
    "official_incident_report",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "live_dispatch",
    "erc8004_reputation_ready",
    "erc8004_reputation_receipt",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "worker_copyable_incident_doctrine",
    "exact_gps_or_raw_metadata_exposure_allowed",
}


def build_incident_verification_internal_package_record(
    *, local_fixture: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the conservative Incident Verification internal package record.

    The record packages one reviewed local fixture into an internal AAS package
    boundary. It proves only packaging continuity; customer output, publication,
    dispatch, reputation, live runtime, exact-location exposure, emergency or
    safety response, repair/insurance/SLA/official-report claims, and
    worker-copyable doctrine remain blocked by default.
    """

    source_fixture = local_fixture or load_incident_verification_local_reviewed_fixture()
    _assert_source_fixture_is_conservative(source_fixture)

    safe_to_claim = _dedupe(
        [
            INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
            *source_fixture.get("safe_to_claim", []),
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_fixture.get("do_not_claim_yet", []),
            *ADDITIONAL_BLOCKED_CLAIMS,
        ]
    )

    reviewed_output = source_fixture["local_fixture"]["reviewed_output"]
    evidence = source_fixture["local_fixture"]["evidence_contract_snapshot"]

    record = {
        "schema": INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SCHEMA,
        "package_id": PACKAGE_ID,
        "scope": SCOPE,
        "package_status": PACKAGE_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_fixture_id": source_fixture["fixture_id"],
        "source_fixture_schema": source_fixture["schema"],
        "source_fixture_file": INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME,
        "source_safe_claims_inherited": [
            INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
            INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "ladder_boundary": {
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "internal_package_record": {
            "record_kind": "adjacent_aas_internal_package_record",
            "review_status": "packaged_internal_only_not_promoted",
            "uses_only_local_reviewed_fixture_artifact": True,
            "customer_copy_changed": False,
            "customer_delivery_allowed": False,
            "publication_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "worker_copyable_doctrine_allowed": False,
            "live_acontext_or_runtime_parity_claimed": False,
            "exact_gps_or_raw_metadata_exposure_allowed": False,
            "emergency_response_claimed": False,
            "safety_certification_claimed": False,
            "repair_diagnosis_or_completion_claimed": False,
            "insurance_adjustment_claimed": False,
            "sla_uptime_claimed": False,
            "official_incident_report_claimed": False,
            "source_artifacts": [
                {
                    "fixture_id": source_fixture["fixture_id"],
                    "source_file": INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME,
                    "source_schema": source_fixture["schema"],
                    "review_status": source_fixture["local_fixture"]["review_status"],
                    "fixture_kind": source_fixture["local_fixture"]["fixture_kind"],
                    "plain_language_status": reviewed_output["plain_language_status"],
                }
            ],
            "packaged_evidence_contract": {
                field: evidence[field] for field in REQUIRED_EVIDENCE_FIELDS
            },
            "packaged_reviewed_output": {
                field: reviewed_output[field] for field in REQUIRED_OUTPUT_FIELDS
            },
            "reviewed_output_schema": source_fixture["local_fixture"][
                "reviewed_output_schema"
            ],
            "package_limitations": [
                "Internal package record only; not a customer-facing incident report.",
                "Synthetic local fixture does not represent a real incident case.",
                "Incident state is observational and bounded to permitted evidence summaries.",
                "Severity taxonomy is not a safety certification, emergency determination, repair diagnosis, insurance adjustment, SLA, or official report.",
                "Follow-on trigger is only an operator next-step suggestion and does not authorize live dispatch.",
                "No publication, catalog, pilot, dispatch, reputation, live runtime, exact-location release, emergency/safety/repair/insurance/SLA/official-report claim, or worker-doctrine readiness is authorized.",
            ],
        },
        "package_review_checks": [
            {
                "check_id": check,
                "status": "passed_for_internal_package_record_only",
                "blocks_promotion_until_later_gate": True,
            }
            for check in PACKAGE_REVIEW_CHECKS
        ],
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "operator_instruction": (
            "Use this only as the Incident Verification internal package record. "
            "The next valid step is a read-only operator coverage surface or "
            "explicit customer-output schema gate, not customer copy, catalog "
            "routing, dispatch, reputation, live Acontext, exact-location release, "
            "emergency/safety/repair/insurance/SLA/official-report claims, or worker-copyable doctrine."
        ),
        "next_smallest_proof": (
            "Create an Incident Verification coverage summary or read-only operator "
            "surface over this internal package record while keeping customer/"
            "public/dispatch/reputation/privacy/emergency/safety/repair/insurance/"
            "SLA/official-report/worker-doctrine readiness false."
        ),
    }
    _assert_package_record_is_conservative(record, source_fixture=source_fixture)
    return record


def write_incident_verification_internal_package_record(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Incident Verification internal package record."""

    record = build_incident_verification_internal_package_record()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_incident_verification_internal_package_record(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Incident Verification internal package record."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        record = json.load(fh)
    if not isinstance(record, dict):
        raise CityOpsContractError(
            "Incident Verification internal package record must be a JSON object"
        )
    _assert_package_record_is_conservative(
        record, source_fixture=load_incident_verification_local_reviewed_fixture()
    )
    return record


def _assert_source_fixture_is_conservative(fixture: dict[str, Any]) -> None:
    if fixture.get("fixture_id") != FIXTURE_ID:
        raise CityOpsContractError("Incident Verification package record source fixture drift")
    if fixture.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Incident Verification package record source family drift")
    if fixture.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Incident Verification package record source offer drift")

    safe_claims = set(fixture.get("safe_to_claim", []))
    for claim in (
        INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
        INCIDENT_VERIFICATION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
        AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    ):
        if claim not in safe_claims:
            raise CityOpsContractError(
                "Incident Verification package record source safe claim missing"
            )

    ladder = fixture.get("ladder_boundary", {})
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Incident Verification package record source promoted readiness")
    local_fixture = fixture.get("local_fixture", {})
    if local_fixture.get("review_status") != "reviewed_internal_fixture_only_not_promoted":
        raise CityOpsContractError("Incident Verification package record source review status drift")
    for flag in (
        "customer_copy_changed",
        "customer_delivery_allowed",
        "publication_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "worker_copyable_doctrine_allowed",
        "emergency_or_safety_claim_allowed",
        "repair_or_insurance_claim_allowed",
        "sla_or_official_report_claim_allowed",
    ):
        if local_fixture.get(flag) is not False:
            raise CityOpsContractError(f"Incident Verification package record source promoted {flag}")
    for flag in READINESS_FALSE_FLAGS:
        if fixture.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Incident Verification package record source promoted readiness: {flag}"
            )


def _assert_package_record_is_conservative(
    record: dict[str, Any], *, source_fixture: dict[str, Any]
) -> None:
    _assert_source_fixture_is_conservative(source_fixture)
    if record.get("schema") != INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SCHEMA:
        raise CityOpsContractError("Incident Verification internal package record schema drift")
    if record.get("package_id") != PACKAGE_ID:
        raise CityOpsContractError("Incident Verification internal package record package_id drift")
    if record.get("scope") != SCOPE:
        raise CityOpsContractError("Incident Verification internal package record scope drift")
    if record.get("package_status") != PACKAGE_STATUS:
        raise CityOpsContractError("Incident Verification internal package record status drift")
    if record.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Incident Verification internal package record family drift")
    if record.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Incident Verification internal package record offer drift")
    if record.get("source_fixture_id") != source_fixture.get("fixture_id"):
        raise CityOpsContractError("Incident Verification internal package record source fixture drift")

    safe_claims = set(record.get("safe_to_claim", []))
    if INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM not in safe_claims:
        raise CityOpsContractError("Incident Verification internal package record safe claim missing")
    if safe_claims & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("Incident Verification internal package record has forbidden safe claims")
    for inherited_claim in record.get("source_safe_claims_inherited", []):
        if inherited_claim not in safe_claims:
            raise CityOpsContractError(
                "Incident Verification internal package record inherited claim missing"
            )

    missing_blocked = (
        set(source_fixture.get("do_not_claim_yet", [])) | set(ADDITIONAL_BLOCKED_CLAIMS)
    ) - set(record.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            "Incident Verification internal package record missing blocked claims: "
            f"{sorted(missing_blocked)}"
        )
    overlap = sorted(safe_claims & set(record.get("do_not_claim_yet", [])))
    if overlap:
        raise CityOpsContractError(
            f"Incident Verification internal package record claim overlap: {overlap}"
        )

    ladder = record.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Incident Verification internal package record covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Incident Verification internal package record next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Incident Verification internal package record promoted readiness")

    for flag in READINESS_FALSE_FLAGS:
        if record.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Incident Verification internal package record promoted readiness: {flag}"
            )

    package = record.get("internal_package_record")
    if not isinstance(package, dict):
        raise CityOpsContractError("Incident Verification internal package payload must be an object")
    if package.get("review_status") != "packaged_internal_only_not_promoted":
        raise CityOpsContractError("Incident Verification internal package review status drift")
    if package.get("uses_only_local_reviewed_fixture_artifact") is not True:
        raise CityOpsContractError("Incident Verification internal package must use local fixture only")
    for false_flag in (
        "customer_copy_changed",
        "customer_delivery_allowed",
        "publication_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "worker_copyable_doctrine_allowed",
        "live_acontext_or_runtime_parity_claimed",
        "exact_gps_or_raw_metadata_exposure_allowed",
        "emergency_response_claimed",
        "safety_certification_claimed",
        "repair_diagnosis_or_completion_claimed",
        "insurance_adjustment_claimed",
        "sla_uptime_claimed",
        "official_incident_report_claimed",
    ):
        if package.get(false_flag) is not False:
            raise CityOpsContractError(f"Incident Verification internal package promoted {false_flag}")

    source_artifacts = package.get("source_artifacts")
    if not isinstance(source_artifacts, list) or len(source_artifacts) != 1:
        raise CityOpsContractError("Incident Verification internal package requires one source artifact")
    source = source_artifacts[0]
    if source.get("fixture_id") != FIXTURE_ID:
        raise CityOpsContractError("Incident Verification internal package source artifact drift")
    if source.get("source_file") != INCIDENT_VERIFICATION_LOCAL_REVIEWED_FIXTURE_FILENAME:
        raise CityOpsContractError("Incident Verification internal package source file drift")

    evidence = package.get("packaged_evidence_contract", {})
    if set(REQUIRED_EVIDENCE_FIELDS) - set(evidence):
        raise CityOpsContractError("Incident Verification internal package lost evidence fields")
    reviewed_output = package.get("packaged_reviewed_output", {})
    if set(REQUIRED_OUTPUT_FIELDS) - set(reviewed_output):
        raise CityOpsContractError("Incident Verification internal package lost reviewed output fields")

    _assert_no_private_location_or_incident_overclaims(package)

    checks = record.get("package_review_checks")
    if not isinstance(checks, list) or len(checks) != len(PACKAGE_REVIEW_CHECKS):
        raise CityOpsContractError("Incident Verification internal package review checks drift")
    check_ids = [item.get("check_id") for item in checks if isinstance(item, dict)]
    if check_ids != PACKAGE_REVIEW_CHECKS:
        raise CityOpsContractError("Incident Verification internal package review check order drift")
    for item in checks:
        if item.get("status") != "passed_for_internal_package_record_only":
            raise CityOpsContractError("Incident Verification internal package review check status drift")
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError(
                "Incident Verification internal package review check stopped blocking promotion"
            )


def _assert_no_private_location_or_incident_overclaims(package: dict[str, Any]) -> None:
    serialized = json.dumps(package, sort_keys=True).lower()
    forbidden_substrings = [
        "latitude",
        "longitude",
        "gps:",
        "gps coordinate:",
        "home address",
        "precise address:",
        "driver license",
        "passport",
        "social security",
        "emergency response completed",
        "emergency dispatch",
        "safety certified",
        "safe for occupancy",
        "repair diagnosed",
        "repair completed",
        "insurance adjustment completed",
        "official incident report filed",
        "sla guaranteed",
        "worker doctrine ready",
    ]
    for substring in forbidden_substrings:
        if substring in serialized:
            raise CityOpsContractError(
                "Incident Verification internal package leaked private location or incident overclaim"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
