"""Retail Reality adjacent-AAS internal/admin read surface.

This module advances Retail Reality as a Service by exactly one rung: from an
internal package record to a read-only operator surface. It remains an
internal/admin visibility surface only. It consumes only the Retail Reality
internal package record and does not register a public route, create catalog or
customer copy, price work, dispatch work, prove live Acontext/runtime parity,
attach ERC-8004 reputation, expose exact GPS/raw metadata, guarantee permanent
business status or inventory, certify brand compliance/safety, judge employees,
or publish worker-copyable retail doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_minimum_ladder_template import READINESS_FALSE_FLAGS
from .contracts import CityOpsContractError
from .retail_reality_fixture_review_gate import (
    ARTIFACT_DIR,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
)
from .retail_reality_internal_package_record import (
    PACKAGE_ID,
    RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME,
    RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SCHEMA,
)

RETAIL_REALITY_OPERATOR_READ_SURFACE_SCHEMA = (
    "city_ops.retail_reality_operator_read_surface.v1"
)
RETAIL_REALITY_OPERATOR_READ_SURFACE_FILENAME = (
    "retail_reality_operator_read_surface.json"
)
RETAIL_REALITY_OPERATOR_READ_SURFACE_SAFE_CLAIM = (
    "retail_reality_operator_read_surface_landed"
)

SURFACE_ID = "execution_market.aas.retail_reality.operator_read_surface.001"
SCOPE = "internal_admin_retail_reality_read_surface_only"
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
    "read_surface_pricing_ready",
    "read_surface_dispatch_ready",
    "read_surface_reputation_ready",
    "read_surface_worker_doctrine_ready",
    "read_surface_live_acontext_ready",
    "read_surface_permanent_status_ready",
    "read_surface_inventory_guarantee_ready",
    "read_surface_brand_compliance_ready",
    "read_surface_employee_performance_ready",
    "read_surface_consumer_safety_ready",
    "retail_reality_operator_surface_public_route_ready",
    "retail_reality_operator_surface_customer_delivery_ready",
    "retail_reality_operator_surface_catalog_ready",
    "retail_reality_operator_surface_pricing_ready",
    "retail_reality_operator_surface_dispatch_ready",
    "retail_reality_operator_surface_reputation_ready",
    "retail_reality_operator_surface_worker_doctrine_ready",
    "retail_reality_operator_surface_live_acontext_ready",
    "retail_reality_operator_surface_permanent_status_ready",
    "retail_reality_operator_surface_inventory_guarantee_ready",
    "retail_reality_operator_surface_brand_compliance_ready",
    "retail_reality_operator_surface_employee_performance_ready",
    "retail_reality_operator_surface_consumer_safety_ready",
    "retail_reality_customer_output_schema_ready",
    "retail_reality_internal_sample_output_ready",
    "retail_reality_operator_approval_ready",
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
    "pilot_authorized",
    "catalog_customer_ready",
    "public_pricing_or_customer_quote_ready",
    "autonomous_dispatch_ready",
    "dispatch_routing_ready",
    "erc8004_reputation_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "worker_copyable_retail_doctrine",
    "live_acontext_ready",
    "runtime_parity_proven",
    "acontext_sink_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "permanent_business_status_claim",
    "inventory_guarantee",
    "brand_compliance_certification",
    "employee_performance_judgment",
    "consumer_safety_claim",
    "storefront_status_guaranteed",
    "inventory_available_guaranteed",
}

_FALSE_ACCESS_FLAGS = [
    "network_route_registered",
    "public_route_registered",
    "customer_visible",
    "catalog_visible",
    "pricing_enabled",
    "worker_visible",
    "dispatch_enabled",
    "writes_live_acontext",
    "writes_municipal_memory",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
    "claims_permanent_business_status",
    "claims_inventory_guarantee",
    "claims_brand_compliance",
    "judges_employee_performance",
    "claims_consumer_safety",
]

_FALSE_DERIVED_FLAGS = [
    "semantic_reinterpretation_performed",
    "reads_raw_review_fixtures",
    "reads_raw_transcripts",
    "reads_raw_photo_metadata",
    "reads_inventory_systems",
    "reads_brand_compliance_systems",
    "writes_customer_copy",
    "writes_catalog_copy",
    "writes_pricing_quote",
    "writes_dispatch_instructions",
    "writes_live_acontext",
    "writes_municipal_memory",
    "enables_dispatch_automation",
    "emits_reputation_receipts",
    "publishes_worker_doctrine",
    "exposes_gps_or_metadata",
    "creates_permanent_business_status_claim",
    "creates_inventory_guarantee",
    "creates_brand_compliance_claim",
    "creates_employee_performance_judgment",
    "creates_consumer_safety_claim",
]

_PACKAGE_FALSE_FLAGS = [
    "customer_copy_changed",
    "customer_delivery_allowed",
    "publication_allowed",
    "catalog_allowed",
    "pricing_quote_allowed",
    "dispatch_allowed",
    "reputation_attachment_allowed",
    "worker_skill_dna_allowed",
    "worker_copyable_doctrine_allowed",
    "live_acontext_or_runtime_parity_claimed",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "permanent_business_status_claim_allowed",
    "inventory_guarantee_allowed",
    "brand_compliance_claim_allowed",
    "employee_performance_judgment_allowed",
    "consumer_safety_claim_allowed",
]

SURFACE_REVIEW_CHECKS = [
    "source_package_safe_claims_present",
    "surface_consumes_only_internal_package_record",
    "source_artifact_ids_and_digest_preserved",
    "access_policy_internal_admin_only",
    "operator_cards_are_pass_through_not_customer_copy",
    "safe_and_blocked_claims_remain_adjacent",
    "no_raw_transcript_exact_location_or_metadata_inputs",
    "customer_public_pricing_dispatch_reputation_runtime_location_status_inventory_"
    "compliance_safety_and_worker_doctrine_still_blocked",
    "next_ladder_steps_require_separate_artifacts",
]


def build_retail_reality_operator_read_surface(
    *, package_record: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the read-only internal/admin Retail Reality operator surface.

    The surface consumes only the Retail Reality internal package record and
    reshapes package state into operator cards without semantic reinterpretation.
    It proves read-only internal visibility, not customer delivery, public or
    catalog exposure, pricing, dispatch, reputation, live runtime parity,
    exact-location release, permanent-status/inventory/compliance/safety claims,
    or worker doctrine.
    """

    source_record = package_record or _load_source_package_record_only()
    _assert_source_package_record_is_conservative(source_record)

    safe_to_claim = _dedupe(
        [
            *source_record.get("safe_to_claim", []),
            RETAIL_REALITY_OPERATOR_READ_SURFACE_SAFE_CLAIM,
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
    source_package_digest = _digest_record(source_record)
    source_artifacts = list(package["source_artifacts"])
    package_state = {flag: package[flag] for flag in _PACKAGE_FALSE_FLAGS}

    surface = {
        "schema": RETAIL_REALITY_OPERATOR_READ_SURFACE_SCHEMA,
        "surface_id": SURFACE_ID,
        "scope": SCOPE,
        "surface_status": SURFACE_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_package_id": source_record["package_id"],
        "source_package_schema": source_record["schema"],
        "source_package_file": RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME,
        "source_package_digest_sha256": source_package_digest,
        "source_safe_claims_inherited": [
            RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
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
            "source_artifacts": [RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME],
            "source_package_digest_sha256": source_package_digest,
            "consumes_only": [RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME],
            "source_artifact_lineage_passed_through": source_artifacts,
            "forbidden_inputs": [
                "raw_transcript",
                "raw_review_fixture",
                "raw_photo_metadata",
                "unreviewed_memory",
                "private_operator_context",
                "live_acontext_transport",
                "gps_or_metadata_payloads",
                "inventory_system",
                "brand_compliance_system",
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
            "suggested_internal_path": "/internal/admin/aas/retail-reality/operator-read-surface",
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
            "source_fixture_count": len(source_artifacts),
            "package_status": source_record["package_status"],
            "review_status": package["review_status"],
            "source_package_digest_sha256": source_package_digest,
            "source_artifact_ids": [artifact.get("fixture_id") for artifact in source_artifacts],
            "required_evidence_fields_present": list(REQUIRED_EVIDENCE_FIELDS),
            "required_output_fields_present": list(REQUIRED_OUTPUT_FIELDS),
            "operator_cards_are_pass_through": True,
            "package_state_passed_through_without_reinterpretation": True,
            "promotion_blocked_until_separate_artifacts": True,
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
                "card": "source_artifact_lineage",
                "status": "package_artifact_ids_and_digest_pass_through",
                "values": {
                    "source_package_id": source_record["package_id"],
                    "source_package_file": RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME,
                    "source_package_digest_sha256": source_package_digest,
                    "source_artifacts": source_artifacts,
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
                "card": "package_state",
                "status": "package_state_pass_through_all_false",
                "values": package_state,
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
                "check_id": check,
                "status": "passed_for_internal_read_surface_only",
                "blocks_promotion_until_later_gate": True,
            }
            for check in SURFACE_REVIEW_CHECKS
        ],
        "operator_instruction": (
            "Use this only as a read-only internal/admin operator surface for the "
            "Retail Reality package record. Do not treat it as customer copy, catalog "
            "copy, pricing authority, dispatch authorization, reputation evidence, "
            "live Acontext parity, exact-location release, permanent-status or "
            "inventory proof, brand/safety certification, employee judgment, or "
            "worker-copyable retail doctrine."
        ),
        "next_smallest_proof": (
            "Create a Retail Reality customer-output schema gate that consumes this "
            "surface and still keeps publication, delivery, catalog, pricing, dispatch, "
            "reputation, runtime, privacy, permanent-status, inventory, compliance, "
            "safety, and worker-doctrine readiness false."
        ),
    }
    _assert_read_surface_is_conservative(surface, source_record=source_record)
    return surface


def write_retail_reality_operator_read_surface(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Retail Reality internal/admin operator read surface."""

    surface = build_retail_reality_operator_read_surface()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / RETAIL_REALITY_OPERATOR_READ_SURFACE_FILENAME
    path.write_text(json.dumps(surface, indent=2) + "\n", encoding="utf-8")
    return path


def load_retail_reality_operator_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Retail Reality read surface."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / RETAIL_REALITY_OPERATOR_READ_SURFACE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        surface = json.load(fh)
    if not isinstance(surface, dict):
        raise CityOpsContractError("Retail Reality operator read surface must be JSON object")
    _assert_read_surface_is_conservative(
        surface,
        source_record=_load_source_package_record_for_dir(source_dir),
    )
    return surface


def _load_source_package_record_for_dir(source_dir: Path) -> dict[str, Any]:
    if (source_dir / RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME).exists():
        return _load_source_package_record_only(artifact_dir=source_dir)
    return _load_source_package_record_only()


def _load_source_package_record_only(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        record = json.load(fh)
    if not isinstance(record, dict):
        raise CityOpsContractError(
            "Retail Reality operator read surface source must be JSON object"
        )
    _assert_source_package_record_is_conservative(record)
    return record


def _assert_source_package_record_is_conservative(record: dict[str, Any]) -> None:
    if record.get("schema") != RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SCHEMA:
        raise CityOpsContractError("Retail Reality read surface source package schema drift")
    if record.get("package_id") != PACKAGE_ID:
        raise CityOpsContractError("Retail Reality read surface source package id drift")
    if record.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Retail Reality read surface source family drift")
    if record.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Retail Reality read surface source offer drift")
    if RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM not in record.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Retail Reality read surface source safe claim missing")
    if record.get("ladder_boundary", {}).get("promotion_allowed") is not False:
        raise CityOpsContractError("Retail Reality read surface source promoted readiness")
    for flag in READINESS_FALSE_FLAGS:
        if record.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality read surface source promoted readiness: {flag}"
            )
    package = record.get("internal_package_record")
    if not isinstance(package, dict):
        raise CityOpsContractError("Retail Reality read surface source package payload missing")
    if package.get("uses_only_local_reviewed_fixture_artifact") is not True:
        raise CityOpsContractError("Retail Reality read surface source package input drift")
    for false_flag in _PACKAGE_FALSE_FLAGS:
        if package.get(false_flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality read surface source promoted {false_flag}"
            )
    evidence = package.get("packaged_evidence_contract", {})
    if not set(REQUIRED_EVIDENCE_FIELDS).issubset(set(evidence.keys())):
        raise CityOpsContractError("Retail Reality read surface source lost evidence fields")
    output = package.get("packaged_reviewed_output", {})
    if not set(REQUIRED_OUTPUT_FIELDS).issubset(set(output.keys())):
        raise CityOpsContractError("Retail Reality read surface source lost output fields")
    source_artifacts = package.get("source_artifacts")
    if not isinstance(source_artifacts, list) or len(source_artifacts) != 1:
        raise CityOpsContractError("Retail Reality read surface source artifacts drift")
    if not source_artifacts[0].get("fixture_id"):
        raise CityOpsContractError("Retail Reality read surface source artifact id missing")


def _assert_read_surface_is_conservative(
    surface: dict[str, Any], *, source_record: dict[str, Any]
) -> None:
    _assert_source_package_record_is_conservative(source_record)
    if surface.get("schema") != RETAIL_REALITY_OPERATOR_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("Retail Reality operator read surface schema drift")
    if surface.get("surface_id") != SURFACE_ID:
        raise CityOpsContractError("Retail Reality operator read surface id drift")
    if surface.get("scope") != SCOPE:
        raise CityOpsContractError("Retail Reality operator read surface scope drift")
    if surface.get("surface_status") != SURFACE_STATUS:
        raise CityOpsContractError("Retail Reality operator read surface status drift")
    if surface.get("source_package_id") != source_record.get("package_id"):
        raise CityOpsContractError("Retail Reality operator read surface source package drift")
    if surface.get("source_package_digest_sha256") != _digest_record(source_record):
        raise CityOpsContractError("Retail Reality operator read surface source digest drift")

    keys = list(surface.keys())
    if keys.index("do_not_claim_yet") != keys.index("safe_to_claim") + 1:
        raise CityOpsContractError(
            "Retail Reality operator read surface separated claim boundaries"
        )
    _assert_claim_boundaries(
        surface.get("safe_to_claim", []), surface.get("do_not_claim_yet", [])
    )
    if RETAIL_REALITY_OPERATOR_READ_SURFACE_SAFE_CLAIM not in surface.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Retail Reality operator read surface safe claim missing")
    if RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM not in surface.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Retail Reality operator read surface source claim missing")
    missing_blocked = (
        set(source_record.get("do_not_claim_yet", [])) | set(READ_SURFACE_BLOCKED_CLAIMS)
    ) - set(surface.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            "Retail Reality operator read surface missing blocked claims: "
            f"{sorted(missing_blocked)}"
        )

    ladder = surface.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Retail Reality operator read surface covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Retail Reality operator read surface next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Retail Reality operator read surface promoted readiness")

    for section_name, flags in (
        ("derived_from", _FALSE_DERIVED_FLAGS),
        ("access_policy", _FALSE_ACCESS_FLAGS),
    ):
        section = surface.get(section_name, {})
        for flag in flags:
            if section.get(flag) is not False:
                raise CityOpsContractError(
                    f"Retail Reality operator read surface {section_name} overclaims {flag}"
                )
    derived = surface.get("derived_from", {})
    if derived.get("consumes_only") != [RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME]:
        raise CityOpsContractError("Retail Reality operator read surface input drift")
    if derived.get("source_artifact_lineage_passed_through") != source_record[
        "internal_package_record"
    ]["source_artifacts"]:
        raise CityOpsContractError("Retail Reality operator read surface source artifacts drift")
    access = surface.get("access_policy", {})
    if access.get("audience") != "internal_admin_only" or access.get(
        "requires_admin_context"
    ) is not True:
        raise CityOpsContractError("Retail Reality operator read surface access policy drift")
    if surface.get("mount_contract", {}).get("network_route_registered") is not False:
        raise CityOpsContractError("Retail Reality operator read surface registered network route")

    for flag in READINESS_FALSE_FLAGS:
        if surface.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality operator read surface promoted readiness: {flag}"
            )

    summary = surface.get("coverage_summary", {})
    if summary.get("covered_package_records") != 1:
        raise CityOpsContractError("Retail Reality operator read surface coverage count drift")
    if summary.get("operator_cards_are_pass_through") is not True:
        raise CityOpsContractError(
            "Retail Reality operator read surface reinterpreted operator cards"
        )
    if summary.get("package_state_passed_through_without_reinterpretation") is not True:
        raise CityOpsContractError(
            "Retail Reality operator read surface reinterpreted package state"
        )
    if summary.get("promotion_blocked_until_separate_artifacts") is not True:
        raise CityOpsContractError(
            "Retail Reality operator read surface stopped blocking promotion"
        )

    cards = surface.get("operator_cards")
    if not isinstance(cards, list) or len(cards) != 7:
        raise CityOpsContractError("Retail Reality operator read surface cards drift")
    cards_by_name = {card.get("card"): card for card in cards if isinstance(card, dict)}
    for required_card in (
        "package_position",
        "source_artifact_lineage",
        "evidence_contract",
        "reviewed_output",
        "package_state",
        "safe_to_claim",
        "do_not_claim_yet",
    ):
        if required_card not in cards_by_name:
            raise CityOpsContractError("Retail Reality operator read surface missing required card")
    if cards_by_name["reviewed_output"].get("status") != (
        "package_payload_pass_through_not_customer_copy"
    ):
        raise CityOpsContractError("Retail Reality operator read surface promoted reviewed output")
    if cards_by_name["evidence_contract"].get("values") != source_record[
        "internal_package_record"
    ]["packaged_evidence_contract"]:
        raise CityOpsContractError("Retail Reality operator read surface reinterpreted evidence")
    if cards_by_name["reviewed_output"].get("values") != source_record[
        "internal_package_record"
    ]["packaged_reviewed_output"]:
        raise CityOpsContractError(
            "Retail Reality operator read surface reinterpreted reviewed output"
        )
    if cards_by_name["package_state"].get("values") != {
        flag: source_record["internal_package_record"][flag] for flag in _PACKAGE_FALSE_FLAGS
    }:
        raise CityOpsContractError(
            "Retail Reality operator read surface reinterpreted package state"
        )

    checks = surface.get("surface_review_checks")
    if (
        not isinstance(checks, list)
        or [item.get("check_id") for item in checks] != SURFACE_REVIEW_CHECKS
    ):
        raise CityOpsContractError("Retail Reality operator read surface review checks drift")
    for item in checks:
        if item.get("status") != "passed_for_internal_read_surface_only":
            raise CityOpsContractError(
                "Retail Reality operator read surface review check status drift"
            )
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError(
                "Retail Reality operator read surface review check stopped blocking promotion"
            )

    _assert_no_private_metadata_or_retail_overclaims(surface)


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    forbidden = sorted(safe & FORBIDDEN_SAFE_CLAIMS)
    if forbidden:
        raise CityOpsContractError(
            f"Retail Reality operator read surface has forbidden safe claims: {forbidden}"
        )
    overlap = sorted(safe & blocked)
    if overlap:
        raise CityOpsContractError(f"Retail Reality operator read surface claim overlap: {overlap}")


def _assert_no_private_metadata_or_retail_overclaims(surface: dict[str, Any]) -> None:
    serialized = json.dumps(surface, sort_keys=True).lower()
    forbidden_fragments = [
        "latitude",
        "longitude",
        "gps:",
        "exact address retained",
        "raw image metadata retained",
        "private staff name was copied",
        "private contact detail was copied",
        "raw transcript is authority",
        "permanent business-status claim allowed",
        "inventory guarantee provided",
        "brand compliance certified",
        "employee performance judgment provided",
        "consumer-safety claim provided",
        "customer delivery authorized",
        "catalog route authorized",
        "pricing quote authorized",
        "dispatch route authorized",
        "reputation receipt authorized",
    ]
    if any(fragment in serialized for fragment in forbidden_fragments):
        raise CityOpsContractError(
            "Retail Reality operator read surface exposed private metadata or overclaimed authority"
        )


def _digest_record(record: dict[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
