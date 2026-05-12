"""Compliance Desk adjacent-AAS internal/admin read surface.

This module advances the Compliance Desk adjacent package by exactly one rung:
from an internal package record to a read-only operator surface. It is still a
contracted internal/admin data surface only. It does not register a public route,
create customer copy, authorize a pilot, dispatch work, prove live Acontext or
runtime parity, attach ERC-8004 reputation, expose exact GPS/raw metadata, or
publish worker-copyable compliance doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import READINESS_FALSE_FLAGS
from .compliance_desk_fixture_review_gate import (
    ARTIFACT_DIR,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
)
from .compliance_desk_internal_package_record import (
    COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_FILENAME,
    COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SCHEMA,
    PACKAGE_ID,
    load_compliance_desk_internal_package_record,
)
from .contracts import CityOpsContractError

COMPLIANCE_DESK_OPERATOR_READ_SURFACE_SCHEMA = (
    "city_ops.compliance_desk_operator_read_surface.v1"
)
COMPLIANCE_DESK_OPERATOR_READ_SURFACE_FILENAME = (
    "compliance_desk_operator_read_surface.json"
)
COMPLIANCE_DESK_OPERATOR_READ_SURFACE_SAFE_CLAIM = (
    "compliance_desk_operator_read_surface_landed"
)

SURFACE_ID = "execution_market.aas.compliance_desk.operator_read_surface.001"
SCOPE = "internal_admin_compliance_desk_read_surface_only"
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
    "compliance_desk_public_route_ready",
    "compliance_desk_customer_output_schema_ready",
    "compliance_desk_internal_sample_output_ready",
    "compliance_desk_operator_approval_ready",
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
]

_FALSE_DERIVED_FLAGS = [
    "semantic_reinterpretation_performed",
    "reads_raw_review_fixtures",
    "reads_raw_transcripts",
    "writes_customer_copy",
    "writes_live_acontext",
    "writes_municipal_memory",
    "enables_dispatch_automation",
    "emits_reputation_receipts",
    "publishes_worker_doctrine",
    "exposes_gps_or_metadata",
]


def build_compliance_desk_operator_read_surface(
    *, package_record: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the read-only internal/admin operator surface.

    The surface consumes only the Compliance Desk internal package record and
    reshapes it into operator cards. It proves read-only visibility, not product
    readiness or public/customer exposure.
    """

    source_record = package_record or load_compliance_desk_internal_package_record()
    _assert_source_package_record_is_conservative(source_record)

    safe_to_claim = _dedupe(
        [
            *source_record.get("safe_to_claim", []),
            COMPLIANCE_DESK_OPERATOR_READ_SURFACE_SAFE_CLAIM,
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
        "schema": COMPLIANCE_DESK_OPERATOR_READ_SURFACE_SCHEMA,
        "surface_id": SURFACE_ID,
        "scope": SCOPE,
        "surface_status": SURFACE_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_package_id": source_record["package_id"],
        "source_package_schema": source_record["schema"],
        "source_package_file": COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_FILENAME,
        "source_safe_claims_inherited": [
            COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
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
            "source_artifacts": [COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_FILENAME],
            "consumes_only": [COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_FILENAME],
            "forbidden_inputs": [
                "raw_transcript",
                "raw_review_fixture",
                "unreviewed_memory",
                "private_operator_context",
                "live_acontext_transport",
                "gps_or_metadata_payloads",
                "freeform_worker_chat",
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
            "suggested_internal_path": "/internal/admin/aas/compliance-desk/operator-read-surface",
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
            "partial_legibility_blocks_promotion": True,
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
                "customer_public_dispatch_reputation_and_worker_doctrine_still_blocked",
                "next_ladder_steps_require_separate_artifacts",
            ]
        ],
        "operator_instruction": (
            "Use this only as a read-only internal/admin operator surface for the "
            "Compliance Desk package record. Do not treat it as customer copy, a "
            "catalog route, dispatch authorization, reputation evidence, live Acontext "
            "parity, exact-location release, or worker-copyable doctrine."
        ),
        "next_smallest_proof": (
            "Create a Compliance Desk customer-output schema gate that consumes this "
            "surface and still keeps publication, delivery, dispatch, reputation, "
            "runtime, privacy, legal/regulator, and worker-doctrine readiness false."
        ),
    }
    _assert_read_surface_is_conservative(surface, source_record=source_record)
    return surface


def write_compliance_desk_operator_read_surface(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Compliance Desk internal/admin read surface."""

    surface = build_compliance_desk_operator_read_surface()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / COMPLIANCE_DESK_OPERATOR_READ_SURFACE_FILENAME
    path.write_text(json.dumps(surface, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_compliance_desk_operator_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Compliance Desk read surface."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / COMPLIANCE_DESK_OPERATOR_READ_SURFACE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        surface = json.load(fh)
    if not isinstance(surface, dict):
        raise CityOpsContractError("Compliance Desk operator read surface must be a JSON object")
    _assert_read_surface_is_conservative(
        surface,
        source_record=_load_source_package_record_for_dir(source_dir),
    )
    return surface


def _load_source_package_record_for_dir(source_dir: Path) -> dict[str, Any]:
    if (source_dir / COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_FILENAME).exists():
        return load_compliance_desk_internal_package_record(artifact_dir=source_dir)
    return load_compliance_desk_internal_package_record()


def _assert_source_package_record_is_conservative(record: dict[str, Any]) -> None:
    if record.get("schema") != COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SCHEMA:
        raise CityOpsContractError("Compliance Desk read surface source package schema drift")
    if record.get("package_id") != PACKAGE_ID:
        raise CityOpsContractError("Compliance Desk read surface source package id drift")
    if record.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Compliance Desk read surface source family drift")
    if record.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Compliance Desk read surface source offer drift")
    if COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM not in record.get("safe_to_claim", []):
        raise CityOpsContractError("Compliance Desk read surface source safe claim missing")
    if record.get("ladder_boundary", {}).get("promotion_allowed") is not False:
        raise CityOpsContractError("Compliance Desk read surface source promoted readiness")
    for flag in READINESS_FALSE_FLAGS:
        if record.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Compliance Desk read surface source promoted readiness: {flag}")
    package = record.get("internal_package_record")
    if not isinstance(package, dict):
        raise CityOpsContractError("Compliance Desk read surface source package payload missing")
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
            raise CityOpsContractError(f"Compliance Desk read surface source promoted {false_flag}")


def _assert_read_surface_is_conservative(
    surface: dict[str, Any], *, source_record: dict[str, Any]
) -> None:
    _assert_source_package_record_is_conservative(source_record)
    if surface.get("schema") != COMPLIANCE_DESK_OPERATOR_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("Compliance Desk operator read surface schema drift")
    if surface.get("surface_id") != SURFACE_ID:
        raise CityOpsContractError("Compliance Desk operator read surface id drift")
    if surface.get("scope") != SCOPE:
        raise CityOpsContractError("Compliance Desk operator read surface scope drift")
    if surface.get("surface_status") != SURFACE_STATUS:
        raise CityOpsContractError("Compliance Desk operator read surface status drift")
    if surface.get("source_package_id") != source_record.get("package_id"):
        raise CityOpsContractError("Compliance Desk operator read surface source package drift")

    _assert_claim_boundaries(surface.get("safe_to_claim", []), surface.get("do_not_claim_yet", []))
    if COMPLIANCE_DESK_OPERATOR_READ_SURFACE_SAFE_CLAIM not in surface.get("safe_to_claim", []):
        raise CityOpsContractError("Compliance Desk operator read surface safe claim missing")
    if COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM not in surface.get("safe_to_claim", []):
        raise CityOpsContractError("Compliance Desk operator read surface source claim missing")
    missing_blocked = (set(source_record.get("do_not_claim_yet", [])) | set(READ_SURFACE_BLOCKED_CLAIMS)) - set(
        surface.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"Compliance Desk operator read surface missing blocked claims: {sorted(missing_blocked)}"
        )

    ladder = surface.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Compliance Desk operator read surface covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Compliance Desk operator read surface next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Compliance Desk operator read surface promoted readiness")

    for section_name, flags in (
        ("derived_from", _FALSE_DERIVED_FLAGS),
        ("access_policy", _FALSE_ACCESS_FLAGS),
    ):
        section = surface.get(section_name, {})
        for flag in flags:
            if section.get(flag) is not False:
                raise CityOpsContractError(f"Compliance Desk operator read surface {section_name} overclaims {flag}")
    access = surface.get("access_policy", {})
    if access.get("audience") != "internal_admin_only" or access.get("requires_admin_context") is not True:
        raise CityOpsContractError("Compliance Desk operator read surface access policy drift")
    if surface.get("mount_contract", {}).get("network_route_registered") is not False:
        raise CityOpsContractError("Compliance Desk operator read surface registered network route")

    for flag in READINESS_FALSE_FLAGS:
        if surface.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Compliance Desk operator read surface promoted readiness: {flag}")

    summary = surface.get("coverage_summary", {})
    if summary.get("covered_package_records") != 1:
        raise CityOpsContractError("Compliance Desk operator read surface coverage count drift")
    if summary.get("partial_legibility_blocks_promotion") is not True:
        raise CityOpsContractError("Compliance Desk operator read surface softened legibility block")
    if summary.get("operator_cards_are_pass_through") is not True:
        raise CityOpsContractError("Compliance Desk operator read surface reinterpreted operator cards")

    cards = surface.get("operator_cards")
    if not isinstance(cards, list) or len(cards) != 6:
        raise CityOpsContractError("Compliance Desk operator read surface cards drift")
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
            raise CityOpsContractError("Compliance Desk operator read surface missing required card")
    if cards_by_name["reviewed_output"].get("status") != "package_payload_pass_through_not_customer_copy":
        raise CityOpsContractError("Compliance Desk operator read surface promoted reviewed output")
    reviewed_output = cards_by_name["reviewed_output"].get("values", {})
    if reviewed_output.get("source_type_split", {}).get("raw_transcript_used_as_authority") is not False:
        raise CityOpsContractError("Compliance Desk operator read surface promoted raw transcript authority")

    checks = surface.get("surface_review_checks")
    if not isinstance(checks, list) or len(checks) != 7:
        raise CityOpsContractError("Compliance Desk operator read surface review checks drift")
    for item in checks:
        if item.get("status") != "passed_for_internal_read_surface_only":
            raise CityOpsContractError("Compliance Desk operator read surface review check status drift")
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError("Compliance Desk operator read surface review check stopped blocking promotion")

    _assert_no_exact_location_or_regulator_claims(surface)


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    forbidden = sorted(safe & FORBIDDEN_SAFE_CLAIMS)
    if forbidden:
        raise CityOpsContractError(f"Compliance Desk operator read surface has forbidden safe claims: {forbidden}")
    overlap = sorted(safe & blocked)
    if overlap:
        raise CityOpsContractError(f"Compliance Desk operator read surface claim overlap: {overlap}")


def _assert_no_exact_location_or_regulator_claims(surface: dict[str, Any]) -> None:
    serialized = json.dumps(surface, sort_keys=True).lower()
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
                "Compliance Desk operator read surface leaked exact location or regulator claim"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
