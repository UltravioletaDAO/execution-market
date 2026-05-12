"""Compliance Desk adjacent-AAS local reviewed fixture.

This module advances the Compliance Desk adjacent package by exactly one rung:
from fixture spec/review gate to a single local reviewed fixture. It remains
internal/admin only. It does not create customer copy, publish a catalog,
authorize a pilot, prove live Acontext/runtime parity, dispatch work, attach
ERC-8004 reputation, expose exact GPS/raw metadata, or create worker-copyable
compliance doctrine.
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
    REQUIRED_BLOCKED_CLAIMS as GATE_BLOCKED_CLAIMS,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
    load_compliance_desk_fixture_review_gate,
)
from .contracts import CityOpsContractError

COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SCHEMA = (
    "city_ops.compliance_desk_local_reviewed_fixture.v1"
)
COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME = (
    "compliance_desk_local_reviewed_fixture.json"
)
COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM = (
    "compliance_desk_local_reviewed_fixture_landed"
)

FIXTURE_ID = "execution_market.aas.compliance_desk.local_reviewed_fixture.001"
SCOPE = "internal_admin_compliance_desk_local_reviewed_fixture_only"

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
    "all_required_evidence_fields_populated",
    "reviewed_output_uses_only_allowed_fields",
    "observed_documented_heard_source_split_preserved",
    "privacy_redaction_completed_for_local_fixture",
    "exact_gps_and_raw_metadata_absent",
    "legal_advice_and_regulator_acceptance_claims_absent",
    "non_guarantee_language_present",
    "customer_public_dispatch_reputation_and_worker_doctrine_still_blocked",
]

ADDITIONAL_BLOCKED_CLAIMS = [
    "local_fixture_customer_delivery_ready",
    "local_fixture_publication_ready",
    "local_fixture_catalog_ready",
    "local_fixture_dispatch_ready",
    "local_fixture_reputation_ready",
    "local_fixture_worker_doctrine_ready",
    "local_fixture_live_acontext_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(GATE_BLOCKED_CLAIMS) | set(ADDITIONAL_BLOCKED_CLAIMS)


def build_compliance_desk_local_reviewed_fixture(
    *, gate: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build one internal reviewed fixture for Compliance Desk.

    The fixture is synthetic and non-jurisdiction-specific. It proves the review
    shape for a visible posting snapshot without claiming legal compliance,
    customer readiness, dispatchability, reputation attachment, live Acontext
    parity, exact location disclosure, or worker-copyable doctrine.
    """

    source_gate = gate or load_compliance_desk_fixture_review_gate()
    _assert_source_gate(source_gate)

    reviewed_output = {
        "task_id_or_local_case_reference": "local_compliance_fixture_visible_posting_001",
        "offer_type": OFFER_ID,
        "plain_language_status": (
            "A required notice appears visible in the scoped public-facing area, "
            "but full-body legibility is only partially confirmed. This is an "
            "operator-reviewed evidence snapshot, not a legal compliance finding."
        ),
        "visible_elements_reviewed": [
            "notice_board_or_posting_area_present",
            "notice_header_visible",
            "notice_date_window_visible",
            "notice_body_partially_legible",
            "no_exact_address_or_gps_in_output",
        ],
        "evidence_summary": [
            "Wide/context visual snapshot shows the expected posting area and one visible notice.",
            "Close visual snapshot confirms the header and date window but not the full body text.",
            "Documented checklist context was used only to define what to look for, not as legal authority.",
            "No exact GPS coordinates, raw metadata, private counter details, or raw transcript are exposed.",
        ],
        "source_type_split": {
            "observed": [
                "posting_area_present",
                "notice_header_visible",
                "date_window_visible",
                "body_text_partially_legible",
            ],
            "documented": [
                "customer_supplied_visible_element_checklist_used_as_review_scope_only"
            ],
            "heard": [],
            "raw_transcript_used_as_authority": False,
        },
        "obstruction_or_legibility_notes": (
            "Glare and distance prevented full-body legibility confirmation from the "
            "permitted vantage point. A recheck should request a closer permitted angle."
        ),
        "what_was_checked": [
            "presence_of_posting_area",
            "presence_of_notice",
            "header_visibility",
            "date_window_visibility",
            "partial_body_legibility",
            "absence_of_exact_location_data_in_reviewed_output",
        ],
        "what_was_not_checked": [
            "legal_sufficiency",
            "regulator_acceptance",
            "complete_notice_body_text",
            "continuous_monitoring",
            "official_inspection",
            "filing_or_permit_approval_outcome",
        ],
        "limitations_and_non_guarantees": [
            "This fixture is synthetic and local; it does not represent a real municipal case.",
            "The review does not certify legal compliance or regulator acceptance.",
            "Partial legibility means the status cannot be promoted to customer-ready pass language.",
            "No customer delivery, public catalog, dispatch route, or ERC-8004 reputation receipt is authorized.",
        ],
        "recommended_next_action": (
            "Create one bounded posting recheck task with explicit close/legibility "
            "requirements, then route the result through a separate internal package "
            "record before any customer-output schema or approval decision."
        ),
        "operator_review_notice": (
            "Reviewed for local fixture shape only. Keep all customer/public/pilot/"
            "dispatch/reputation/live-runtime/worker-doctrine readiness false."
        ),
    }

    fixture = {
        "schema": COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SCHEMA,
        "fixture_id": FIXTURE_ID,
        "scope": SCOPE,
        "package_family_id": PACKAGE_FAMILY_ID,
        "offer_id": OFFER_ID,
        "source_gate_id": source_gate["gate_id"],
        "source_gate_schema": source_gate["schema"],
        "source_safe_claims_inherited": [
            COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "safe_to_claim": [
            COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
            COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
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
            "fixture_kind": "synthetic_non_jurisdiction_specific_visible_posting_snapshot",
            "customer_copy_changed": False,
            "customer_delivery_allowed": False,
            "publication_allowed": False,
            "dispatch_allowed": False,
            "reputation_attachment_allowed": False,
            "worker_copyable_doctrine_allowed": False,
            "evidence_contract_snapshot": {
                "wide_context_photo_or_permitted_visual_snapshot": (
                    "synthetic permitted visual snapshot: exterior posting area visible; "
                    "no street address, exact coordinates, or raw metadata retained"
                ),
                "close_notice_or_required_element_photo_where_allowed": (
                    "synthetic close snapshot: notice header and date window visible; "
                    "body text partially obstructed"
                ),
                "timestamp_window": "relative_business_day_window_no_exact_location",
                "visible_element_checklist": [
                    "posting_area_present",
                    "notice_header_visible",
                    "notice_date_window_visible",
                    "notice_body_partially_legible",
                    "exact_location_data_removed",
                ],
                "source_type_observed_documented_or_heard": {
                    "observed": True,
                    "documented": True,
                    "heard": False,
                    "raw_transcript_used_as_authority": False,
                },
                "obstruction_or_legibility_notes": (
                    "glare and distance limit the body-text review; fixture remains partial"
                ),
                "reviewed_limitations": [
                    "not_legal_advice",
                    "not_regulator_acceptance",
                    "not_customer_ready",
                    "not_publication_ready",
                    "not_dispatch_ready",
                ],
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
            "Use this fixture only to prove the Compliance Desk reviewed-output shape. "
            "The next valid step is an internal package record, not customer copy, "
            "catalog routing, dispatch, reputation, live Acontext, or worker-copyable doctrine."
        ),
        "next_smallest_proof": (
            "Create a Compliance Desk internal package record that consumes this local "
            "fixture and keeps customer/public/dispatch/reputation/privacy/worker-doctrine "
            "readiness false."
        ),
    }
    _assert_fixture_is_conservative(fixture, source_gate=source_gate)
    return fixture


def write_compliance_desk_local_reviewed_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Compliance Desk local reviewed fixture."""

    fixture = build_compliance_desk_local_reviewed_fixture()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_compliance_desk_local_reviewed_fixture(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Compliance Desk local reviewed fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        fixture = json.load(fh)
    if not isinstance(fixture, dict):
        raise CityOpsContractError("Compliance Desk local reviewed fixture must be a JSON object")
    _assert_fixture_is_conservative(fixture, source_gate=load_compliance_desk_fixture_review_gate())
    return fixture


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if gate.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Compliance Desk local fixture source gate family drift")
    if gate.get("fixture_spec", {}).get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Compliance Desk local fixture source gate offer drift")
    safe_claims = set(gate.get("safe_to_claim", []))
    for claim in (
        COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
        AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    ):
        if claim not in safe_claims:
            raise CityOpsContractError("Compliance Desk local fixture source safe claim missing")
    gate_ladder = gate.get("ladder_boundary", {})
    if gate_ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Compliance Desk local fixture source gate promoted readiness")


def _assert_fixture_is_conservative(
    fixture: dict[str, Any], *, source_gate: dict[str, Any]
) -> None:
    _assert_source_gate(source_gate)
    if fixture.get("schema") != COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SCHEMA:
        raise CityOpsContractError("Compliance Desk local reviewed fixture schema drift")
    if fixture.get("scope") != SCOPE:
        raise CityOpsContractError("Compliance Desk local reviewed fixture scope drift")
    if fixture.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Compliance Desk local reviewed fixture family drift")
    if fixture.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Compliance Desk local reviewed fixture offer drift")
    if fixture.get("source_gate_id") != source_gate.get("gate_id"):
        raise CityOpsContractError("Compliance Desk local reviewed fixture source gate drift")

    safe_claims = set(fixture.get("safe_to_claim", []))
    if COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM not in safe_claims:
        raise CityOpsContractError("Compliance Desk local reviewed fixture safe claim missing")
    if safe_claims & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("Compliance Desk local reviewed fixture has forbidden safe claims")
    for inherited_claim in fixture.get("source_safe_claims_inherited", []):
        if inherited_claim not in safe_claims:
            raise CityOpsContractError("Compliance Desk local reviewed fixture inherited claim missing")

    missing_blocked = (set(GATE_BLOCKED_CLAIMS) | set(ADDITIONAL_BLOCKED_CLAIMS)) - set(
        fixture.get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"Compliance Desk local reviewed fixture missing blocked claims: {sorted(missing_blocked)}"
        )

    ladder = fixture.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Compliance Desk local reviewed fixture covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Compliance Desk local reviewed fixture next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Compliance Desk local reviewed fixture promoted readiness")

    readiness = fixture.get("readiness", {})
    for flag in READINESS_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"Compliance Desk local reviewed fixture promoted readiness: {flag}")

    local_fixture = fixture.get("local_fixture")
    if not isinstance(local_fixture, dict):
        raise CityOpsContractError("Compliance Desk local fixture payload must be an object")
    if local_fixture.get("review_status") != "reviewed_internal_fixture_only_not_promoted":
        raise CityOpsContractError("Compliance Desk local fixture review status drift")
    for false_flag in (
        "customer_copy_changed",
        "customer_delivery_allowed",
        "publication_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "worker_copyable_doctrine_allowed",
    ):
        if local_fixture.get(false_flag) is not False:
            raise CityOpsContractError(f"Compliance Desk local fixture promoted {false_flag}")

    evidence = local_fixture.get("evidence_contract_snapshot", {})
    if set(REQUIRED_EVIDENCE_FIELDS) - set(evidence):
        raise CityOpsContractError("Compliance Desk local fixture lost required evidence fields")
    source_split = evidence.get("source_type_observed_documented_or_heard", {})
    if source_split.get("raw_transcript_used_as_authority") is not False:
        raise CityOpsContractError("Compliance Desk local fixture promoted raw transcript authority")

    schema = local_fixture.get("reviewed_output_schema", {})
    if not set(REQUIRED_OUTPUT_FIELDS).issubset(set(schema.get("required_fields", []))):
        raise CityOpsContractError("Compliance Desk local fixture lost required output fields")
    forbidden_fields = set(schema.get("forbidden_fields", []))
    for field in (
        "exact_gps_coordinates",
        "raw_metadata_blob",
        "legal_advice_or_legal_sufficiency",
        "regulator_acceptance_claim",
        "worker_copyable_compliance_doctrine",
    ):
        if field not in forbidden_fields:
            raise CityOpsContractError("Compliance Desk local fixture lost forbidden output fields")

    reviewed_output = local_fixture.get("reviewed_output", {})
    if set(REQUIRED_OUTPUT_FIELDS) - set(reviewed_output):
        raise CityOpsContractError("Compliance Desk local fixture reviewed output lost required fields")
    source_type_split = reviewed_output.get("source_type_split", {})
    if source_type_split.get("raw_transcript_used_as_authority") is not False:
        raise CityOpsContractError("Compliance Desk local fixture promoted raw transcript authority")
    _assert_no_exact_location_or_regulator_claims(reviewed_output)

    checks = fixture.get("local_review_checks")
    if not isinstance(checks, list) or len(checks) != len(LOCAL_FIXTURE_REVIEW_CHECKS):
        raise CityOpsContractError("Compliance Desk local fixture review checks drift")
    check_ids = [item.get("check_id") for item in checks if isinstance(item, dict)]
    if check_ids != LOCAL_FIXTURE_REVIEW_CHECKS:
        raise CityOpsContractError("Compliance Desk local fixture review check order drift")
    for item in checks:
        if item.get("status") != "passed_for_local_fixture_only":
            raise CityOpsContractError("Compliance Desk local fixture review check status drift")
        if item.get("blocks_promotion_until_later_gate") is not True:
            raise CityOpsContractError("Compliance Desk local fixture review check stopped blocking promotion")


def _assert_no_exact_location_or_regulator_claims(reviewed_output: dict[str, Any]) -> None:
    serialized = json.dumps(reviewed_output, sort_keys=True).lower()
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
                "Compliance Desk local fixture leaked exact location or regulator claim"
            )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
