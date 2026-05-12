"""Compliance Desk adjacent-AAS internal package record.

This module advances the Compliance Desk adjacent package by exactly one rung:
from a local reviewed fixture to an internal package record. It remains an
internal/admin packaging artifact. It does not create customer copy, publish a
catalog, authorize a pilot, prove live Acontext/runtime parity, dispatch work,
attach ERC-8004 reputation, expose exact GPS/raw metadata, or create
worker-copyable compliance doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    READINESS_FALSE_FLAGS,
)
from .compliance_desk_fixture_review_gate import (
    ARTIFACT_DIR,
    COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
)
from .compliance_desk_local_reviewed_fixture import (
    COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME,
    COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
    FIXTURE_ID,
    load_compliance_desk_local_reviewed_fixture,
)
from .contracts import CityOpsContractError

COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SCHEMA = (
    "city_ops.compliance_desk_internal_package_record.v1"
)
COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_FILENAME = (
    "compliance_desk_internal_package_record.json"
)
COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM = (
    "compliance_desk_internal_package_record_landed"
)

PACKAGE_ID = "execution_market.aas.compliance_desk.internal_package_record.001"
SCOPE = "internal_admin_compliance_desk_package_record_only"
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
    "evidence_and_reviewed_output_fields_preserved",
    "privacy_redaction_and_no_exact_location_preserved",
    "legal_regulator_and_guarantee_claims_absent",
    "customer_public_dispatch_reputation_and_worker_doctrine_still_blocked",
    "next_ladder_steps_require_separate_artifacts",
]

ADDITIONAL_BLOCKED_CLAIMS = [
    "internal_package_customer_delivery_ready",
    "internal_package_publication_ready",
    "internal_package_catalog_ready",
    "internal_package_dispatch_ready",
    "internal_package_reputation_ready",
    "internal_package_worker_doctrine_ready",
    "internal_package_live_acontext_ready",
    "internal_package_approval_ready",
    "compliance_desk_customer_ready",
    "compliance_desk_catalog_ready",
    "compliance_desk_dispatch_ready",
    "compliance_desk_reputation_ready",
    "compliance_desk_worker_doctrine_ready",
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
    "legal_compliance",
    "legal_sufficiency",
    "regulator_acceptance",
    "official_inspection",
    "continuous_monitoring",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "erc8004_reputation_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "worker_copyable_compliance_doctrine",
    "exact_gps_or_raw_metadata_exposure_allowed",
}



def build_compliance_desk_internal_package_record(
    *, local_fixture: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the conservative Compliance Desk internal package record.

    The record packages one reviewed local fixture into an internal AAS package
    boundary. It proves only packaging continuity; customer output, publication,
    dispatch, reputation, live runtime, exact-location exposure, legal/regulator
    claims, and worker-copyable doctrine remain blocked by default.
    """

    source_fixture = local_fixture or load_compliance_desk_local_reviewed_fixture()
    _assert_source_fixture_is_conservative(source_fixture)

    safe_to_claim = _dedupe(
        [
            COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
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
        "schema": COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SCHEMA,
        "package_id": PACKAGE_ID,
        "scope": SCOPE,
        "package_status": PACKAGE_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_fixture_id": source_fixture["fixture_id"],
        "source_fixture_schema": source_fixture["schema"],
        "source_fixture_file": COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME,
        "source_safe_claims_inherited": [
            COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
            COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
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
            "source_artifacts": [
                {
                    "fixture_id": source_fixture["fixture_id"],
                    "source_file": COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME,
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
                "Internal package record only; not a customer-facing compliance report.",
                "Synthetic local fixture does not represent a real municipal case.",
                "Partial legibility remains a limitation and blocks pass/fail compliance language.",
                "No publication, catalog, pilot, dispatch, reputation, legal, regulator, or worker-doctrine readiness is authorized.",
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
            "Use this only as the Compliance Desk internal package record. The next "
            "valid step is a read-only operator coverage surface or explicit customer-"
            "output schema gate, not customer copy, catalog routing, dispatch, "
            "reputation, live Acontext, exact-location release, or worker-copyable doctrine."
        ),
        "next_smallest_proof": (
            "Create a Compliance Desk coverage summary or read-only operator surface "
            "over this internal package record while keeping customer/public/dispatch/"
            "reputation/privacy/worker-doctrine readiness false."
        ),
    }
    _assert_package_record_is_conservative(record, source_fixture=source_fixture)
    return record



def write_compliance_desk_internal_package_record(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Compliance Desk internal package record."""

    record = build_compliance_desk_internal_package_record()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_FILENAME
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path



def load_compliance_desk_internal_package_record(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Compliance Desk internal package record."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        record = json.load(fh)
    if not isinstance(record, dict):
        raise CityOpsContractError("Compliance Desk internal package record must be a JSON object")
    _assert_package_record_is_conservative(
        record, source_fixture=load_compliance_desk_local_reviewed_fixture()
    )
    return record



def _assert_source_fixture_is_conservative(fixture: dict[str, Any]) -> None:
    if fixture.get("fixture_id") != FIXTURE_ID:
        raise CityOpsContractError("Compliance Desk package record source fixture drift")
    if fixture.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Compliance Desk package record source family drift")
    if fixture.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Compliance Desk package record source offer drift")

    safe_claims = set(fixture.get("safe_to_claim", []))
    for claim in (
        COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
        COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
        AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    ):
        if claim not in safe_claims:
            raise CityOpsContractError("Compliance Desk package record source safe claim missing")

    ladder = fixture.get("ladder_boundary", {})
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Compliance Desk package record source promoted readiness")
    local_fixture = fixture.get("local_fixture", {})
    if local_fixture.get("review_status") != "reviewed_internal_fixture_only_not_promoted":
        raise CityOpsContractError("Compliance Desk package record source review status drift")
    for flag in (
        "customer_copy_changed",
        "customer_delivery_allowed",
        "publication_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "worker_copyable_doctrine_allowed",
    ):
        if local_fixture.get(flag) is not False:
            raise CityOpsContractError(f"Compliance Desk package record source promoted {flag}")
    for flag in READINESS_FALSE_FLAGS:
        if fixture.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Compliance Desk package record source promoted readiness: {flag}")



def _assert_package_record_is_conservative(
    record: dict[str, Any], *, source_fixture: dict[str, Any]
) -> None:
    _assert_source_fixture_is_conservative(source_fixture)
    if record.get("schema") != COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SCHEMA:
        raise CityOpsContractError("Compliance Desk internal package record schema drift")
    if record.get("package_id") != PACKAGE_ID:
        raise CityOpsContractError("Compliance Desk internal package record package_id drift")
    if record.get("scope") != SCOPE:
        raise CityOpsContractError("Compliance Desk internal package record scope drift")
    if record.get("package_status") != PACKAGE_STATUS:
        raise CityOpsContractError("Compliance Desk internal package record status drift")
    if record.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Compliance Desk internal package record family drift")
    if record.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Compliance Desk internal package record offer drift")
    if record.get("source_fixture_id") != source_fixture.get("fixture_id"):
        raise CityOpsContractError("Compliance Desk internal package record source fixture drift")

    safe_claims = set(record.get("safe_to_claim", []))
    if COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM not in safe_claims:
        raise CityOpsContractError("Compliance Desk internal package record safe claim missing")
    if safe_claims & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("Compliance Desk internal package record has forbidden safe claims")
    for inherited_claim in record.get("source_safe_claims_inherited", []):
        if inherited_claim not in safe_claims:
            raise CityOpsContractError("Compliance Desk internal package record inherited claim missing")

    missing_blocked = (set(source_fixture.get("do_not_claim_yet", [])) | set(ADDITIONAL_BLOCKED_CLAIMS)) - set(
        record.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"Compliance Desk internal package record missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = sorted(safe_claims & set(record.get("do_not_claim_yet", [])))
    if overlap:
        raise CityOpsContractError(f"Compliance Desk internal package record claim overlap: {overlap}")

    ladder = record.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Compliance Desk internal package record covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Compliance Desk internal package record next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Compliance Desk internal package record promoted readiness")

    for flag in READINESS_FALSE_FLAGS:
        if record.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Compliance Desk internal package record promoted readiness: {flag}")

    package = record.get("internal_package_record")
    if not isinstance(package, dict):
        raise CityOpsContractError("Compliance Desk internal package payload must be an object")
    if package.get("review_status") != "packaged_internal_only_not_promoted":
        raise CityOpsContractError("Compliance Desk internal package review status drift")
    if package.get("uses_only_local_reviewed_fixture_artifact") is not True:
        raise CityOpsContractError("Compliance Desk internal package must use local fixture only")
    for false_flag in (
        "customer_copy_changed",
        "customer_delivery_allowed",
        "publication_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "worker_copyable_doctrine_allowed",
        "live_acontext_or_runtime_parity_claimed",
        "exact_gps_or_raw_metadata_exposure_allowed",
    ):
        if package.get(false_flag) is not False:
            raise CityOpsContractError(f"Compliance Desk internal package promoted {false_flag}")

    source_artifacts = package.get("source_artifacts")
    if not isinstance(source_artifacts, list) or len(source_artifacts) != 1:
        raise CityOpsContractError("Compliance Desk internal package requires one source artifact")
    source = source_artifacts[0]
    if source.get("fixture_id") != FIXTURE_ID:
        raise CityOpsContractError("Compliance Desk internal package source artifact drift")
    if source.get("source_file") != COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME:
        raise CityOpsContractError("Compliance Desk internal package source file drift")

    evidence = package.get("packaged_evidence_contract", {})
    if set(REQUIRED_EVIDENCE_FIELDS) - set(evidence):
        raise CityOpsContractError("Compliance Desk internal package lost evidence fields")
    reviewed_output = package.get("packaged_reviewed_output", {})
    if set(REQUIRED_OUTPUT_FIELDS) - set(reviewed_output):
        raise CityOpsContractError("Compliance Desk internal package lost reviewed output fields")
    source_type_split = reviewed_output.get("source_type_split", {})
    if source_type_split.get("raw_transcript_used_as_authority") is not False:
        raise CityOpsContractError("Compliance Desk internal package promoted raw transcript authority")
    _assert_no_exact_location_or_regulator_claims(package)

    checks = record.get("package_review_checks")
    if not isinstance(checks, list) or len(checks) != len(PACKAGE_REVIEW_CHECKS):
        raise CityOpsContractError("Compliance Desk internal package review checks drift")
    check_ids = [item.get("check_id") for item in checks if isinstance(item, dict)]
    if check_ids != PACKAGE_REVIEW_CHECKS:
        raise CityOpsContractError("Compliance Desk internal package review check order drift")
    for item in checks:
        if item.get("status") != "passed_for_internal_package_record_only":
            raise CityOpsContractError("Compliance Desk internal package review check status drift")
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError("Compliance Desk internal package review check stopped blocking promotion")



def _assert_no_exact_location_or_regulator_claims(package: dict[str, Any]) -> None:
    serialized = json.dumps(package, sort_keys=True).lower()
    forbidden_substrings = [
        "latitude",
        "longitude",
        "gps:",
        "guaranteed compliance",
        "regulator accepted",
        "officially inspected",
        "legal sufficiency confirmed",
    ]
    for substring in forbidden_substrings:
        if substring in serialized:
            raise CityOpsContractError(
                "Compliance Desk internal package leaked exact location or regulator claim"
            )



def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
