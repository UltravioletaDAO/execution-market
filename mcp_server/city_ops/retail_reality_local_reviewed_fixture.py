"""Retail Reality adjacent-AAS local reviewed fixture.

This module advances Retail Reality as a Service by exactly one rung after the
fixture/review gate: one synthetic local reviewed storefront hours +
availability fixture. It remains internal/admin only. It does not create
customer copy, publish a catalog, authorize a pilot, prove live
Acontext/runtime parity, dispatch work, attach ERC-8004 reputation, expose
exact GPS/raw metadata, or create worker-copyable retail doctrine.
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
    REQUIRED_BLOCKED_CLAIMS as GATE_BLOCKED_CLAIMS,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
    RETAIL_REALITY_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    load_retail_reality_fixture_review_gate,
)

RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SCHEMA = (
    "city_ops.retail_reality_local_reviewed_fixture.v1"
)
RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME = (
    "retail_reality_local_reviewed_fixture.json"
)
RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM = (
    "retail_reality_local_reviewed_fixture_landed"
)

FIXTURE_ID = "execution_market.aas.retail_reality.local_reviewed_fixture.001"
SCOPE = "internal_admin_retail_reality_local_reviewed_fixture_only"

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
    "all_required_retail_evidence_fields_populated",
    "reviewed_output_uses_only_allowed_fields",
    "one_storefront_one_window_one_question_boundary_preserved",
    "posted_hours_and_observed_state_are_source_bounded_not_permanent_status",
    "staff_answer_source_type_preserved_without_private_identity_exposure",
    "availability_observation_preserved_without_inventory_guarantee",
    "discrepancy_summary_and_uncertainty_note_preserved",
    "privacy_redaction_completed_for_local_fixture",
    "exact_gps_raw_metadata_private_staff_identity_and_raw_transcript_absent",
    "brand_compliance_employee_performance_consumer_safety_claims_absent",
    "non_guarantee_language_present",
    "customer_public_dispatch_reputation_and_worker_doctrine_still_blocked",
]

ADDITIONAL_BLOCKED_CLAIMS = [
    "retail_reality_local_fixture_customer_delivery_ready",
    "retail_reality_local_fixture_publication_ready",
    "retail_reality_local_fixture_catalog_ready",
    "retail_reality_local_fixture_pricing_ready",
    "retail_reality_local_fixture_dispatch_ready",
    "retail_reality_local_fixture_reputation_ready",
    "retail_reality_local_fixture_worker_skill_dna_ready",
    "retail_reality_local_fixture_worker_doctrine_ready",
    "retail_reality_local_fixture_live_acontext_ready",
    "retail_reality_local_fixture_permanent_status_ready",
    "retail_reality_local_fixture_inventory_guarantee_ready",
    "retail_reality_local_fixture_brand_compliance_ready",
    "retail_reality_local_fixture_employee_performance_ready",
    "retail_reality_local_fixture_consumer_safety_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(GATE_BLOCKED_CLAIMS) | set(ADDITIONAL_BLOCKED_CLAIMS)


def build_retail_reality_local_reviewed_fixture(
    *, gate: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build one internal reviewed fixture for Retail Reality.

    The fixture is synthetic and non-business-specific. It proves only that the
    local review shape can carry a bounded storefront observation without
    leaking exact location metadata, private staff identity, permanent status,
    inventory guarantees, compliance judgments, customer/public readiness,
    dispatch, reputation attachment, live Acontext parity, or worker-copyable
    retail doctrine.
    """

    source_gate = gate or load_retail_reality_fixture_review_gate()
    _assert_source_gate(source_gate)

    reviewed_output = {
        "task_id_or_local_case_reference": "local_retail_reality_fixture_001",
        "offer_type": OFFER_ID,
        "plain_language_observation_status": (
            "A bounded storefront hours + availability observation was reviewed "
            "inside one synthetic observation window. The output records what was "
            "posted, what was observed, and what remained uncertain. It is not a "
            "permanent business-status claim, not an inventory guarantee, not brand "
            "compliance certification, not employee performance judgment, and not a "
            "consumer-safety claim."
        ),
        "observed_open_closed_or_unable_to_determine_state": (
            "observed_open_during_synthetic_window_source_bounded_not_permanent_status"
        ),
        "posted_hours_summary": (
            "Posted-hours source was represented as a redacted synthetic storefront "
            "hours indicator for the scoped window only; no exact address, GPS "
            "coordinate, raw image metadata, or private staff identity is retained."
        ),
        "availability_or_service_state_summary": (
            "A single service-availability question was answered as observed_available "
            "for the scoped window only. This does not guarantee inventory, future "
            "availability, brand compliance, safety, or suitability."
        ),
        "source_type_summary": (
            "Sources are summarized only by type: posted_hours_source plus "
            "storefront_observation_source plus optional staff_answer_source_type. No "
            "private staff name, private contact detail, raw transcript, or identity "
            "artifact is exposed."
        ),
        "discrepancy_summary": (
            "No discrepancy was detected between the synthetic posted-hours indicator "
            "and the observed open state inside the scoped window; future state remains "
            "unchecked and unclaimed."
        ),
        "observation_window_summary": (
            "Single synthetic observation window only; no exact GPS, raw timestamp "
            "metadata, camera metadata, address, or route trace is included."
        ),
        "what_was_checked": [
            "one_storefront_context_snapshot_source_type",
            "posted_hours_or_open_closed_state_indicator",
            "single_observation_window",
            "one_availability_or_service_question",
            "source_type_classification_without_private_identity",
            "discrepancy_and_uncertainty_language",
            "absence_of_exact_gps_raw_metadata_private_staff_identity_and_raw_transcript",
        ],
        "what_was_not_checked": [
            "permanent_business_status",
            "future_hours_or_future_availability",
            "inventory_count_or_inventory_guarantee",
            "brand_compliance",
            "employee_performance",
            "consumer_safety",
            "pricing_quote",
            "customer_delivery_readiness",
            "dispatch_readiness",
            "erc8004_reputation_readiness",
        ],
        "limitations_and_non_guarantees": [
            "This fixture is synthetic and local; it does not represent a real storefront case.",
            "The review covers one storefront-style observation window and one question only.",
            "The observed state is source-bounded and not a permanent business-status claim.",
            "Availability language is an observation, not an inventory guarantee or future promise.",
            "Source identity is summarized by type; private staff identity and private contact details are blocked.",
            "No customer delivery, public catalog, pricing quote, dispatch route, or ERC-8004 reputation receipt is authorized.",
        ],
        "recommended_next_action": (
            "Create a Retail Reality internal package record that consumes this local "
            "fixture and keeps customer/public/pricing/dispatch/reputation/privacy/"
            "worker-doctrine readiness false."
        ),
        "operator_review_notice": (
            "Reviewed for local fixture shape only. Keep all customer/public/catalog/"
            "pricing/dispatch/reputation/live-runtime/permanent-status/inventory/"
            "brand-compliance/safety/worker-doctrine readiness false."
        ),
    }

    fixture = {
        "schema": RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SCHEMA,
        "fixture_id": FIXTURE_ID,
        "scope": SCOPE,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_gate_id": source_gate["gate_id"],
        "source_gate_schema": source_gate["schema"],
        "source_safe_claims_inherited": [
            RETAIL_REALITY_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "safe_to_claim": [
            RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
            RETAIL_REALITY_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
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
            "fixture_kind": "synthetic_non_business_specific_storefront_hours_availability_check",
            "customer_copy_changed": False,
            "customer_delivery_allowed": False,
            "publication_allowed": False,
            "catalog_allowed": False,
            "pricing_quote_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "worker_skill_dna_allowed": False,
            "worker_copyable_doctrine_allowed": False,
            "permanent_business_status_claim_allowed": False,
            "inventory_guarantee_allowed": False,
            "brand_compliance_claim_allowed": False,
            "employee_performance_judgment_allowed": False,
            "consumer_safety_claim_allowed": False,
            "evidence_contract_snapshot": {
                "storefront_context_photo_or_permitted_visual_snapshot": (
                    "redacted_synthetic_storefront_context_source_type_no_exact_location_or_raw_metadata"
                ),
                "posted_hours_or_open_closed_state_proof": (
                    "posted_hours_indicator_and_observed_open_state_inside_single_window"
                ),
                "observation_window": (
                    "relative_synthetic_window_no_exact_timestamp_gps_address_or_route_trace"
                ),
                "staff_answer_source_type_where_available": (
                    "staff_answer_source_type_only_no_private_staff_identity_or_raw_transcript"
                ),
                "availability_or_service_observed_state": (
                    "single_service_question_observed_available_for_window_only_no_inventory_guarantee"
                ),
                "discrepancy_summary_between_posted_and_observed_state": (
                    "no_synthetic_discrepancy_detected_future_status_unchecked"
                ),
                "uncertainty_note": (
                    "future_hours_future_availability_inventory_safety_and_compliance_not_checked"
                ),
                "what_was_not_checked": (
                    "permanent_status_inventory_guarantee_brand_compliance_employee_performance_consumer_safety"
                ),
            },
            "reviewed_output_schema": {
                "status": "local_reviewed_fixture_internal_only_not_customer_output",
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
            "Use this only as the Retail Reality local reviewed fixture. The next "
            "valid step is an internal package record; do not convert it into customer "
            "copy, catalog listing, pricing quote, dispatch, reputation, live memory, "
            "or worker-copyable retail doctrine."
        ),
        "next_smallest_proof": (
            "Create a Retail Reality internal package record that consumes this local "
            "fixture, summarizes coverage, and preserves all customer/public/pricing/"
            "dispatch/reputation/runtime/GPS/domain-authority/worker-doctrine blocks."
        ),
    }
    _assert_fixture_is_conservative(fixture, source_gate)
    return fixture


def write_retail_reality_local_reviewed_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Retail Reality local reviewed fixture."""

    fixture = build_retail_reality_local_reviewed_fixture()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_retail_reality_local_reviewed_fixture(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Retail Reality local reviewed fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        fixture = json.load(fh)
    if not isinstance(fixture, dict):
        raise CityOpsContractError("Retail Reality local reviewed fixture must be a JSON object")
    _assert_fixture_is_conservative(fixture, load_retail_reality_fixture_review_gate())
    return fixture


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if gate.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Retail Reality local fixture source gate family drift")
    if RETAIL_REALITY_FIXTURE_REVIEW_GATE_SAFE_CLAIM not in gate.get("safe_to_claim", []):
        raise CityOpsContractError("Retail Reality local fixture source gate safe claim missing")
    if gate.get("ladder_boundary", {}).get("promotion_allowed") is not False:
        raise CityOpsContractError("Retail Reality local fixture source gate promoted readiness")
    spec = gate.get("fixture_spec", {})
    if spec.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Retail Reality local fixture source gate offer drift")
    if spec.get("customer_copy_changed") is not False:
        raise CityOpsContractError("Retail Reality local fixture source gate promoted customer copy")
    if not set(REQUIRED_EVIDENCE_FIELDS).issubset(
        set(spec.get("required_evidence_fields", []))
    ):
        raise CityOpsContractError("Retail Reality local fixture source gate lost evidence fields")


def _assert_fixture_is_conservative(
    fixture: dict[str, Any], source_gate: dict[str, Any]
) -> None:
    _assert_source_gate(source_gate)
    if fixture.get("schema") != RETAIL_REALITY_LOCAL_REVIEWED_FIXTURE_SCHEMA:
        raise CityOpsContractError("Retail Reality local reviewed fixture schema drift")
    if fixture.get("scope") != SCOPE:
        raise CityOpsContractError("Retail Reality local reviewed fixture scope drift")
    if fixture.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Retail Reality local reviewed fixture family drift")
    if fixture.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Retail Reality local reviewed fixture offer drift")
    if fixture.get("source_gate_id") != source_gate.get("gate_id"):
        raise CityOpsContractError("Retail Reality local reviewed fixture source gate drift")
    if set(fixture.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("Retail Reality local reviewed fixture has forbidden safe claims")
    missing_blocked = set(GATE_BLOCKED_CLAIMS + ADDITIONAL_BLOCKED_CLAIMS) - set(
        fixture.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"Retail Reality local reviewed fixture missing blocked claims: {sorted(missing_blocked)}"
        )

    ladder = fixture.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Retail Reality local reviewed fixture covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Retail Reality local reviewed fixture next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Retail Reality local reviewed fixture promoted readiness")

    readiness = fixture.get("readiness", {})
    for flag in READINESS_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"Retail Reality local reviewed fixture promoted readiness: {flag}"
            )

    local_fixture = fixture.get("local_fixture")
    if not isinstance(local_fixture, dict):
        raise CityOpsContractError("Retail Reality local reviewed fixture local_fixture missing")
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
        if local_fixture.get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality local reviewed fixture promoted {flag}")

    evidence = local_fixture.get("evidence_contract_snapshot", {})
    if not set(REQUIRED_EVIDENCE_FIELDS).issubset(set(evidence.keys())):
        raise CityOpsContractError("Retail Reality local reviewed fixture lost evidence fields")
    schema = local_fixture.get("reviewed_output_schema", {})
    if not set(REQUIRED_OUTPUT_FIELDS).issubset(set(schema.get("required_fields", []))):
        raise CityOpsContractError("Retail Reality local reviewed fixture lost output fields")
    output = local_fixture.get("reviewed_output", {})
    if not set(REQUIRED_OUTPUT_FIELDS).issubset(set(output.keys())):
        raise CityOpsContractError("Retail Reality local reviewed fixture output missing fields")

    joined_output = json.dumps(output, sort_keys=True).lower()
    forbidden_fragments = [
        "gps coordinate retained",
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
        "dispatch route authorized",
        "reputation receipt authorized",
    ]
    if any(fragment in joined_output for fragment in forbidden_fragments):
        raise CityOpsContractError(
            "Retail Reality local reviewed fixture exposed private metadata or overclaimed authority"
        )
    required_non_guarantees = [
        "not a permanent business-status claim",
        "not an inventory guarantee",
        "not brand compliance certification",
        "not employee performance judgment",
        "not a consumer-safety claim",
    ]
    if not all(fragment in joined_output for fragment in required_non_guarantees):
        raise CityOpsContractError("Retail Reality local reviewed fixture missing non-guarantee language")

    checks = fixture.get("local_review_checks")
    if not isinstance(checks, list) or [item.get("check_id") for item in checks] != LOCAL_FIXTURE_REVIEW_CHECKS:
        raise CityOpsContractError("Retail Reality local reviewed fixture review checks drift")
    for item in checks:
        if item.get("status") != "passed_for_local_fixture_only":
            raise CityOpsContractError("Retail Reality local reviewed fixture check status drift")
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError(
                "Retail Reality local reviewed fixture check stopped blocking promotion"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
