"""Retail Reality adjacent-AAS internal package record.

This module advances Retail Reality as a Service by exactly one rung: from a
local reviewed fixture to an internal package record. It remains internal/admin
only. It does not create customer copy, publish a catalog, authorize a pilot,
prove live Acontext/runtime parity, dispatch work, attach ERC-8004 reputation,
expose exact GPS/raw metadata, guarantee permanent business status or inventory,
certify brand compliance/safety, judge employees, or create worker-copyable
retail doctrine.
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
from .retail_reality_fixture_review_gate import (
    ARTIFACT_DIR,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
    RETAIL_REALITY_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
)
from .retail_reality_local_reviewed_fixture import (
    FIXTURE_ID,
    RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME,
    RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
    load_retail_reality_local_reviewed_fixture,
)

RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SCHEMA = (
    "city_ops.retail_reality_internal_package_record.v1"
)
RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME = (
    "retail_reality_internal_package_record.json"
)
RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM = (
    "retail_reality_internal_package_record_landed"
)

PACKAGE_ID = "execution_market.aas.retail_reality.internal_package_record.001"
SCOPE = "internal_admin_retail_reality_package_record_only"
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
    "package_uses_only_retail_local_reviewed_fixture_artifact",
    "storefront_hours_and_availability_fields_preserved",
    "one_storefront_one_window_one_question_boundary_preserved",
    "posted_hours_and_observed_state_remain_source_bounded_not_permanent_status",
    "staff_answer_source_type_preserved_without_private_identity_or_raw_transcript",
    "availability_observation_preserved_without_inventory_guarantee",
    "brand_compliance_employee_performance_and_consumer_safety_claims_absent",
    "privacy_redaction_exact_location_and_raw_metadata_blocks_preserved",
    "customer_public_pricing_dispatch_reputation_runtime_and_worker_doctrine_still_blocked",
    "next_ladder_steps_require_separate_artifacts",
]

ADDITIONAL_BLOCKED_CLAIMS = [
    "retail_reality_internal_package_customer_delivery_ready",
    "retail_reality_internal_package_publication_ready",
    "retail_reality_internal_package_catalog_ready",
    "retail_reality_internal_package_pricing_ready",
    "retail_reality_internal_package_dispatch_ready",
    "retail_reality_internal_package_reputation_ready",
    "retail_reality_internal_package_worker_skill_dna_ready",
    "retail_reality_internal_package_worker_doctrine_ready",
    "retail_reality_internal_package_live_acontext_ready",
    "retail_reality_internal_package_approval_ready",
    "retail_reality_internal_package_permanent_status_ready",
    "retail_reality_internal_package_inventory_guarantee_ready",
    "retail_reality_internal_package_brand_compliance_ready",
    "retail_reality_internal_package_employee_performance_ready",
    "retail_reality_internal_package_consumer_safety_ready",
    "retail_reality_customer_ready",
    "retail_reality_catalog_ready",
    "retail_reality_pricing_ready",
    "retail_reality_dispatch_ready",
    "retail_reality_reputation_ready",
    "retail_reality_worker_doctrine_ready",
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


def build_retail_reality_internal_package_record(
    *, local_fixture: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the conservative Retail Reality internal package record.

    The record packages one reviewed local fixture into an internal AAS package
    boundary. It proves only packaging continuity; customer output, publication,
    pricing, dispatch, reputation, live runtime, exact-location exposure,
    permanent status, inventory guarantees, compliance/safety certification,
    employee judgment, and worker-copyable doctrine remain blocked by default.
    """

    source_fixture = local_fixture or load_retail_reality_local_reviewed_fixture()
    _assert_source_fixture_is_conservative(source_fixture)

    safe_to_claim = _dedupe(
        [
            RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
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
        "schema": RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SCHEMA,
        "package_id": PACKAGE_ID,
        "scope": SCOPE,
        "package_status": PACKAGE_STATUS,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_fixture_id": source_fixture["fixture_id"],
        "source_fixture_schema": source_fixture["schema"],
        "source_fixture_file": RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME,
        "source_safe_claims_inherited": [
            RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
            RETAIL_REALITY_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
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
            "catalog_allowed": False,
            "pricing_quote_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "worker_skill_dna_allowed": False,
            "worker_copyable_doctrine_allowed": False,
            "live_acontext_or_runtime_parity_claimed": False,
            "exact_gps_or_raw_metadata_exposure_allowed": False,
            "permanent_business_status_claim_allowed": False,
            "inventory_guarantee_allowed": False,
            "brand_compliance_claim_allowed": False,
            "employee_performance_judgment_allowed": False,
            "consumer_safety_claim_allowed": False,
            "source_artifacts": [
                {
                    "fixture_id": source_fixture["fixture_id"],
                    "source_file": RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME,
                    "source_schema": source_fixture["schema"],
                    "review_status": source_fixture["local_fixture"]["review_status"],
                    "fixture_kind": source_fixture["local_fixture"]["fixture_kind"],
                    "plain_language_observation_status": reviewed_output[
                        "plain_language_observation_status"
                    ],
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
                "Internal package record only; not a customer-facing storefront report.",
                "Synthetic local fixture does not represent a real storefront case.",
                "Open/closed and availability language is source-bounded to one scoped observation window only.",
                "Posted-hours proof is a local observation artifact, not a permanent business-status claim.",
                "Availability language is not an inventory guarantee, future promise, or suitability claim.",
                "Staff answer sources are summarized by source type only; private staff identity and raw transcripts stay excluded.",
                "No brand compliance certification, employee performance judgment, consumer-safety claim, publication, catalog, pilot, pricing quote, dispatch, reputation, live runtime, exact metadata release, or worker-doctrine readiness is authorized.",
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
            "Use this only as the Retail Reality internal package record. The next "
            "valid step is a read-only operator coverage surface or customer-output "
            "schema gate, not customer copy, catalog routing, pricing, dispatch, "
            "reputation, live Acontext, exact-location release, permanent status, "
            "inventory guarantees, brand/safety certification, employee judgment, or "
            "worker-copyable retail doctrine."
        ),
        "next_smallest_proof": (
            "Create a Retail Reality read-only operator coverage surface over this "
            "internal package record while keeping customer/public/pricing/dispatch/"
            "reputation/privacy/runtime/permanent-status/inventory/compliance/safety/"
            "worker-doctrine readiness false."
        ),
    }
    _assert_package_record_is_conservative(record, source_fixture=source_fixture)
    return record


def write_retail_reality_internal_package_record(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Retail Reality internal package record."""

    record = build_retail_reality_internal_package_record()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_retail_reality_internal_package_record(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Retail Reality internal package record."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        record = json.load(fh)
    if not isinstance(record, dict):
        raise CityOpsContractError("Retail Reality internal package record must be JSON object")
    _assert_package_record_is_conservative(
        record, source_fixture=load_retail_reality_local_reviewed_fixture()
    )
    return record


def _assert_source_fixture_is_conservative(fixture: dict[str, Any]) -> None:
    if fixture.get("schema") != "city_ops.retail_reality_local_reviewed_fixture.v1":
        raise CityOpsContractError("Retail Reality internal package source schema drift")
    if fixture.get("fixture_id") != FIXTURE_ID:
        raise CityOpsContractError("Retail Reality internal package source fixture drift")
    if fixture.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Retail Reality internal package source family drift")
    if fixture.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Retail Reality internal package source offer drift")
    if RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM not in fixture.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Retail Reality internal package source safe claim missing")
    if fixture.get("ladder_boundary", {}).get("promotion_allowed") is not False:
        raise CityOpsContractError("Retail Reality internal package source promoted readiness")
    if fixture.get("local_fixture", {}).get("review_status") != (
        "reviewed_internal_fixture_only_not_promoted"
    ):
        raise CityOpsContractError("Retail Reality internal package source review status drift")
    for flag in [
        "customer_copy_changed",
        "customer_delivery_allowed",
        "publication_allowed",
        "catalog_allowed",
        "pricing_quote_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "worker_skill_dna_allowed",
        "worker_copyable_doctrine_allowed",
        "permanent_business_status_claim_allowed",
        "inventory_guarantee_allowed",
        "brand_compliance_claim_allowed",
        "employee_performance_judgment_allowed",
        "consumer_safety_claim_allowed",
    ]:
        if fixture.get("local_fixture", {}).get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality internal package source promoted {flag}")


def _assert_package_record_is_conservative(
    record: dict[str, Any], *, source_fixture: dict[str, Any]
) -> None:
    _assert_source_fixture_is_conservative(source_fixture)
    if record.get("schema") != RETAIL_REALITY_INTERNAL_PACKAGE_RECORD_SCHEMA:
        raise CityOpsContractError("Retail Reality internal package record schema drift")
    if record.get("package_id") != PACKAGE_ID:
        raise CityOpsContractError("Retail Reality internal package record id drift")
    if record.get("scope") != SCOPE:
        raise CityOpsContractError("Retail Reality internal package record scope drift")
    if record.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Retail Reality internal package record family drift")
    if record.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Retail Reality internal package record offer drift")
    if record.get("source_fixture_id") != source_fixture.get("fixture_id"):
        raise CityOpsContractError("Retail Reality internal package source fixture drift")
    if set(record.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("Retail Reality internal package record has forbidden safe claims")
    missing_blocked = set(ADDITIONAL_BLOCKED_CLAIMS) - set(record.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"Retail Reality internal package record missing blocked claims: {sorted(missing_blocked)}"
        )

    ladder = record.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Retail Reality internal package record covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Retail Reality internal package record next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Retail Reality internal package record promoted readiness")

    readiness = record.get("readiness", {})
    for flag in READINESS_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality internal package record promoted readiness: {flag}"
            )

    package = record.get("internal_package_record")
    if not isinstance(package, dict):
        raise CityOpsContractError("Retail Reality internal package record package missing")
    for flag in [
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
    ]:
        if package.get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality internal package record promoted {flag}")

    evidence = package.get("packaged_evidence_contract", {})
    if not set(REQUIRED_EVIDENCE_FIELDS).issubset(set(evidence.keys())):
        raise CityOpsContractError("Retail Reality internal package record lost evidence fields")
    schema = package.get("reviewed_output_schema", {})
    if not set(REQUIRED_OUTPUT_FIELDS).issubset(set(schema.get("required_fields", []))):
        raise CityOpsContractError("Retail Reality internal package record lost output fields")
    output = package.get("packaged_reviewed_output", {})
    if not set(REQUIRED_OUTPUT_FIELDS).issubset(set(output.keys())):
        raise CityOpsContractError("Retail Reality internal package record output missing fields")

    joined_package = json.dumps(package, sort_keys=True).lower()
    forbidden_fragments = [
        "gps coordinate retained",
        "raw image metadata retained",
        "exact address retained",
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
    if any(fragment in joined_package for fragment in forbidden_fragments):
        raise CityOpsContractError(
            "Retail Reality internal package record exposed private metadata or overclaimed authority"
        )
    required_non_guarantees = [
        "not a permanent business-status claim",
        "not an inventory guarantee",
        "not brand compliance certification",
        "not employee performance judgment",
        "not a consumer-safety claim",
    ]
    if not all(fragment in joined_package for fragment in required_non_guarantees):
        raise CityOpsContractError("Retail Reality internal package record missing non-guarantee language")

    checks = record.get("package_review_checks")
    if not isinstance(checks, list) or [item.get("check_id") for item in checks] != PACKAGE_REVIEW_CHECKS:
        raise CityOpsContractError("Retail Reality internal package record review checks drift")
    for item in checks:
        if item.get("status") != "passed_for_internal_package_record_only":
            raise CityOpsContractError("Retail Reality internal package record check status drift")
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError(
                "Retail Reality internal package record check stopped blocking promotion"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
