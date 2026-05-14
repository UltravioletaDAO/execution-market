"""Incident Verification adjacent-AAS internal/admin read surface.

This module advances Incident Verification by exactly one rung: from an internal
package record to a read-only operator surface. It remains a contracted
internal/admin visibility surface only. It does not register a public route,
create customer copy, authorize a pilot, dispatch work, prove live Acontext or
runtime parity, attach ERC-8004 reputation, expose exact GPS/raw metadata,
create emergency/safety/repair/insurance/SLA/official-report claims, or publish
worker-copyable incident doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import READINESS_FALSE_FLAGS
from .contracts import CityOpsContractError
from .incident_verification_fixture_review_gate import (
    ARTIFACT_DIR,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
)
from .incident_verification_internal_package_record import (
    INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME,
    INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SCHEMA,
    PACKAGE_ID,
    load_incident_verification_internal_package_record,
)

INCIDENT_VERIFICATION_OPERATOR_READ_SURFACE_SCHEMA = (
    "city_ops.incident_verification_operator_read_surface.v1"
)
INCIDENT_VERIFICATION_OPERATOR_READ_SURFACE_FILENAME = (
    "incident_verification_operator_read_surface.json"
)
INCIDENT_VERIFICATION_OPERATOR_READ_SURFACE_SAFE_CLAIM = (
    "incident_verification_operator_read_surface_landed"
)

SURFACE_ID = "execution_market.aas.incident_verification.operator_read_surface.001"
SCOPE = "internal_admin_incident_verification_read_surface_only"
SURFACE_STATUS = "read_only_operator_surface_landed_not_public_not_customer_ready"

COVERED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "review_gate_checklist",
    "reviewed_output_schema",
    "local_reviewed_fixture",
    "internal_package_record",
    "coverage_summary_or_read_only_operator_surface",
]
NEXT_REQUIRED_LADDER_STEPS = [
    "customer_output_schema_gate",
    "internal_sample_output",
    "explicit_approval_or_hold_decision",
]

READ_SURFACE_BLOCKED_CLAIMS = [
    "read_surface_public_route_ready",
    "read_surface_customer_delivery_ready",
    "read_surface_publication_ready",
    "read_surface_catalog_ready",
    "read_surface_dispatch_ready",
    "read_surface_reputation_ready",
    "read_surface_worker_doctrine_ready",
    "read_surface_live_acontext_ready",
    "incident_verification_public_route_ready",
    "incident_verification_customer_output_schema_ready",
    "incident_verification_internal_sample_output_ready",
    "incident_verification_operator_approval_ready",
    "incident_verification_emergency_ready",
    "incident_verification_safety_certification_ready",
    "incident_verification_repair_ready",
    "incident_verification_insurance_ready",
    "incident_verification_sla_ready",
    "incident_verification_official_report_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(READ_SURFACE_BLOCKED_CLAIMS) | {
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

_FALSE_ACCESS_FLAGS = [
    "network_route_registered",
    "public_route_registered",
    "customer_visible",
    "worker_visible",
    "dispatch_enabled",
    "writes_live_acontext",
    "writes_municipal_memory",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
    "emergency_response_enabled",
    "safety_certification_enabled",
    "repair_diagnosis_enabled",
    "insurance_adjustment_enabled",
    "official_report_enabled",
]

_FALSE_DERIVED_FLAGS = [
    "semantic_reinterpretation_performed",
    "reads_raw_review_fixtures",
    "reads_raw_transcripts",
    "reads_raw_photo_metadata",
    "writes_customer_copy",
    "writes_live_acontext",
    "writes_municipal_memory",
    "enables_dispatch_automation",
    "emits_reputation_receipts",
    "publishes_worker_doctrine",
    "exposes_gps_or_metadata",
    "creates_emergency_response_claim",
    "creates_safety_certification_claim",
    "creates_repair_diagnosis_claim",
    "creates_insurance_adjustment_claim",
    "creates_official_report_claim",
]


def build_incident_verification_operator_read_surface(
    *, package_record: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the read-only internal/admin Incident Verification surface.

    The surface consumes only the Incident Verification internal package record
    and reshapes it into operator cards. It proves read-only visibility, not
    customer delivery, public/catalog exposure, dispatch, reputation, emergency
    response, safety certification, repair/insurance/SLA/official-report
    readiness, live runtime parity, exact-location release, or worker doctrine.
    """

    source_record = package_record or load_incident_verification_internal_package_record()
    _assert_source_package_record_is_conservative(source_record)

    safe_to_claim = _dedupe(
        [
            *source_record.get("safe_to_claim", []),
            INCIDENT_VERIFICATION_OPERATOR_READ_SURFACE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_record.get("do_not_claim_yet", []),
            *READ_SURFACE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    package = source_record["internal_package_record"]
    reviewed_output = package["packaged_reviewed_output"]
    evidence = package["packaged_evidence_contract"]

    surface = {
        "schema": INCIDENT_VERIFICATION_OPERATOR_READ_SURFACE_SCHEMA,
        "surface_id": SURFACE_ID,
        "scope": SCOPE,
        "surface_status": SURFACE_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_package_id": source_record["package_id"],
        "source_package_schema": source_record["schema"],
        "source_package_file": INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME,
        "source_safe_claims_inherited": [
            INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
        ],
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "ladder_boundary": {
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME],
            "consumes_only": [INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME],
            "forbidden_inputs": [
                "raw_transcript",
                "raw_review_fixture",
                "raw_photo_metadata",
                "unreviewed_memory",
                "private_operator_context",
                "live_acontext_transport",
                "gps_or_metadata_payloads",
                "freeform_worker_chat",
                "emergency_dispatch_feed",
                "repair_or_insurance_system",
                "official_reporting_system",
            ],
            **{flag: False for flag in _FALSE_DERIVED_FLAGS},
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **{flag: False for flag in _FALSE_ACCESS_FLAGS},
        },
        "mount_contract": {
            "mount_status": "internal_admin_read_surface_contract_landed_not_network_route",
            "method": "GET",
            "suggested_internal_path": "/internal/admin/aas/incident-verification/operator-read-surface",
            "network_route_registered": False,
            "response_fields": [
                "coverage_summary",
                "operator_cards",
                "safe_to_claim",
                "do_not_claim_yet",
                "readiness",
            ],
        },
        "coverage_summary": {
            "covered_package_records": 1,
            "source_fixture_count": len(package["source_artifacts"]),
            "package_status": source_record["package_status"],
            "review_status": package["review_status"],
            "required_evidence_fields_present": list(REQUIRED_EVIDENCE_FIELDS),
            "required_output_fields_present": list(REQUIRED_OUTPUT_FIELDS),
            "incident_question_blocks_generic_status_copy": True,
            "observational_taxonomy_blocks_safety_certification": True,
            "operator_trigger_blocks_live_dispatch": True,
            "operator_cards_are_pass_through": True,
        },
        "operator_cards": [
            {
                "card": "package_position",
                "status": "visible_internal_admin_only",
                "values": {
                    "package_id": source_record["package_id"],
                    "offer_id": source_record["offer_id"],
                    "covered_steps": list(COVERED_LADDER_STEPS),
                    "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
                },
            },
            {
                "card": "evidence_contract",
                "status": "package_payload_pass_through_no_raw_metadata",
                "values": {field: evidence[field] for field in REQUIRED_EVIDENCE_FIELDS},
            },
            {
                "card": "reviewed_output",
                "status": "package_payload_pass_through_not_customer_copy",
                "values": {field: reviewed_output[field] for field in REQUIRED_OUTPUT_FIELDS},
            },
            {
                "card": "limitations",
                "status": "visible_without_softening",
                "values": list(package["package_limitations"]),
            },
            {
                "card": "safe_to_claim",
                "status": "visible_without_softening",
                "values": list(safe_to_claim),
            },
            {
                "card": "do_not_claim_yet",
                "status": "visible_without_softening",
                "values": list(do_not_claim_yet),
            },
        ],
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "surface_review_checks": [
            {
                "check_id": check_id,
                "status": "passed_for_internal_read_surface_only",
                "blocks_promotion_until_later_gate": True,
            }
            for check_id in [
                "source_package_safe_claims_present",
                "surface_consumes_only_internal_package_record",
                "access_policy_internal_admin_only",
                "operator_cards_are_pass_through_not_customer_copy",
                "no_raw_transcript_exact_location_or_metadata_inputs",
                "emergency_safety_repair_insurance_sla_and_official_report_still_blocked",
                "customer_public_dispatch_reputation_and_worker_doctrine_still_blocked",
                "next_ladder_steps_require_separate_artifacts",
            ]
        ],
        "operator_instruction": (
            "Use this only as a read-only internal/admin operator surface for the "
            "Incident Verification package record. Do not treat it as customer copy, "
            "a catalog route, dispatch authorization, reputation evidence, live Acontext "
            "parity, exact-location release, emergency response, safety certification, "
            "repair/insurance/SLA/official-report readiness, or worker-copyable doctrine."
        ),
        "next_smallest_proof": (
            "Create an Incident Verification customer-output schema gate that consumes this "
            "surface and still keeps publication, delivery, dispatch, reputation, runtime, "
            "privacy, emergency/safety/repair/insurance/SLA/official-report, and worker-doctrine readiness false."
        ),
    }
    _assert_read_surface_is_conservative(surface, source_record=source_record)
    return surface


def write_incident_verification_operator_read_surface(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Incident Verification internal/admin read surface."""

    surface = build_incident_verification_operator_read_surface()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / INCIDENT_VERIFICATION_OPERATOR_READ_SURFACE_FILENAME
    path.write_text(json.dumps(surface, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_incident_verification_operator_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Incident Verification read surface."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / INCIDENT_VERIFICATION_OPERATOR_READ_SURFACE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        surface = json.load(fh)
    if not isinstance(surface, dict):
        raise CityOpsContractError("Incident Verification operator read surface must be a JSON object")
    _assert_read_surface_is_conservative(
        surface,
        source_record=_load_source_package_record_for_dir(source_dir),
    )
    return surface


def _load_source_package_record_for_dir(source_dir: Path) -> dict[str, Any]:
    if (source_dir / INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_FILENAME).exists():
        return load_incident_verification_internal_package_record(artifact_dir=source_dir)
    return load_incident_verification_internal_package_record()


def _assert_source_package_record_is_conservative(record: dict[str, Any]) -> None:
    if record.get("schema") != INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SCHEMA:
        raise CityOpsContractError("Incident Verification read surface source package schema drift")
    if record.get("package_id") != PACKAGE_ID:
        raise CityOpsContractError("Incident Verification read surface source package id drift")
    if record.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Incident Verification read surface source family drift")
    if record.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Incident Verification read surface source offer drift")
    if INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM not in record.get("safe_to_claim", []):
        raise CityOpsContractError("Incident Verification read surface source safe claim missing")
    if record.get("ladder_boundary", {}).get("promotion_allowed") is not False:
        raise CityOpsContractError("Incident Verification read surface source promoted readiness")
    for flag in READINESS_FALSE_FLAGS:
        if record.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Incident Verification read surface source promoted readiness: {flag}")
    package = record.get("internal_package_record")
    if not isinstance(package, dict):
        raise CityOpsContractError("Incident Verification read surface source package payload missing")
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
            raise CityOpsContractError(f"Incident Verification read surface source promoted {false_flag}")


def _assert_read_surface_is_conservative(
    surface: dict[str, Any], *, source_record: dict[str, Any]
) -> None:
    _assert_source_package_record_is_conservative(source_record)
    if surface.get("schema") != INCIDENT_VERIFICATION_OPERATOR_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("Incident Verification operator read surface schema drift")
    if surface.get("surface_id") != SURFACE_ID:
        raise CityOpsContractError("Incident Verification operator read surface id drift")
    if surface.get("scope") != SCOPE:
        raise CityOpsContractError("Incident Verification operator read surface scope drift")
    if surface.get("surface_status") != SURFACE_STATUS:
        raise CityOpsContractError("Incident Verification operator read surface status drift")
    if surface.get("source_package_id") != source_record.get("package_id"):
        raise CityOpsContractError("Incident Verification operator read surface source package drift")

    _assert_claim_boundaries(surface.get("safe_to_claim", []), surface.get("do_not_claim_yet", []))
    if INCIDENT_VERIFICATION_OPERATOR_READ_SURFACE_SAFE_CLAIM not in surface.get("safe_to_claim", []):
        raise CityOpsContractError("Incident Verification operator read surface safe claim missing")
    if INCIDENT_VERIFICATION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM not in surface.get("safe_to_claim", []):
        raise CityOpsContractError("Incident Verification operator read surface source claim missing")
    missing_blocked = (set(source_record.get("do_not_claim_yet", [])) | set(READ_SURFACE_BLOCKED_CLAIMS)) - set(
        surface.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"Incident Verification operator read surface missing blocked claims: {sorted(missing_blocked)}"
        )

    ladder = surface.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Incident Verification operator read surface covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Incident Verification operator read surface next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Incident Verification operator read surface promoted readiness")

    for section_name, flags in (
        ("derived_from", _FALSE_DERIVED_FLAGS),
        ("access_policy", _FALSE_ACCESS_FLAGS),
    ):
        section = surface.get(section_name, {})
        for flag in flags:
            if section.get(flag) is not False:
                raise CityOpsContractError(f"Incident Verification operator read surface {section_name} overclaims {flag}")
    access = surface.get("access_policy", {})
    if access.get("audience") != "internal_admin_only" or access.get("requires_admin_context") is not True:
        raise CityOpsContractError("Incident Verification operator read surface access policy drift")
    if surface.get("mount_contract", {}).get("network_route_registered") is not False:
        raise CityOpsContractError("Incident Verification operator read surface registered network route")

    for flag in READINESS_FALSE_FLAGS:
        if surface.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Incident Verification operator read surface promoted readiness: {flag}")

    summary = surface.get("coverage_summary", {})
    if summary.get("covered_package_records") != 1:
        raise CityOpsContractError("Incident Verification operator read surface coverage count drift")
    if summary.get("incident_question_blocks_generic_status_copy") is not True:
        raise CityOpsContractError("Incident Verification operator read surface softened incident question block")
    if summary.get("observational_taxonomy_blocks_safety_certification") is not True:
        raise CityOpsContractError("Incident Verification operator read surface softened safety-certification block")
    if summary.get("operator_trigger_blocks_live_dispatch") is not True:
        raise CityOpsContractError("Incident Verification operator read surface softened dispatch block")
    if summary.get("operator_cards_are_pass_through") is not True:
        raise CityOpsContractError("Incident Verification operator read surface reinterpreted operator cards")

    cards = surface.get("operator_cards")
    if not isinstance(cards, list) or len(cards) != 6:
        raise CityOpsContractError("Incident Verification operator read surface cards drift")
    cards_by_name = {card.get("card"): card for card in cards if isinstance(card, dict)}
    for required_card in (
        "package_position",
        "evidence_contract",
        "reviewed_output",
        "limitations",
        "safe_to_claim",
        "do_not_claim_yet",
    ):
        if required_card not in cards_by_name:
            raise CityOpsContractError("Incident Verification operator read surface missing required card")
    if cards_by_name["reviewed_output"].get("status") != "package_payload_pass_through_not_customer_copy":
        raise CityOpsContractError("Incident Verification operator read surface promoted reviewed output")
    reviewed_output = cards_by_name["reviewed_output"].get("values", {})
    serialized_review = json.dumps(reviewed_output, sort_keys=True).lower()
    for required_phrase in (
        "not emergency response",
        "not a safety certification",
        "not an official incident report",
        "do not auto-dispatch",
    ):
        if required_phrase not in serialized_review:
            raise CityOpsContractError("Incident Verification operator read surface lost incident bounds")

    checks = surface.get("surface_review_checks")
    if not isinstance(checks, list) or len(checks) != 8:
        raise CityOpsContractError("Incident Verification operator read surface review checks drift")
    for item in checks:
        if item.get("status") != "passed_for_internal_read_surface_only":
            raise CityOpsContractError("Incident Verification operator read surface review check status drift")
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError("Incident Verification operator read surface review check stopped blocking promotion")

    _assert_no_private_location_or_incident_overclaims(surface)


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    forbidden = sorted(safe & FORBIDDEN_SAFE_CLAIMS)
    if forbidden:
        raise CityOpsContractError(f"Incident Verification operator read surface has forbidden safe claims: {forbidden}")
    overlap = sorted(safe & blocked)
    if overlap:
        raise CityOpsContractError(f"Incident Verification operator read surface claim overlap: {overlap}")


def _assert_no_private_location_or_incident_overclaims(surface: dict[str, Any]) -> None:
    serialized = json.dumps(surface, sort_keys=True).lower()
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
                "Incident Verification operator read surface leaked private location or incident overclaim"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
