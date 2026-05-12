"""Compliance Desk adjacent-AAS fixture spec and review-gate checklist.

This module instantiates the first adjacent AAS package from the minimum ladder:
Compliance Desk as a Service. It deliberately stops at an internal fixture spec
and review-gate checklist. It does not create customer copy, publish a catalog,
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
    REQUIRED_BLOCKED_CLAIMS as TEMPLATE_BLOCKED_CLAIMS,
    REQUIRED_LADDER_STEPS,
    load_aas_minimum_ladder_template,
)
from .contracts import CityOpsContractError

COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SCHEMA = (
    "city_ops.compliance_desk_fixture_review_gate.v1"
)
COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_FILENAME = (
    "compliance_desk_fixture_review_gate.json"
)
COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM = (
    "compliance_desk_fixture_review_gate_landed"
)

PACKAGE_FAMILY_ID = "compliance_desk_as_a_service"
OFFER_ID = "visible_posting_notice_compliance_snapshot"
SCOPE = "internal_admin_compliance_desk_fixture_spec_and_review_gate_only"
ARTIFACT_DIR = Path(__file__).resolve().parent / "fixtures" / "aas_package_ladder"

COVERED_LADDER_STEPS = [
    "narrow_concierge_offer_card",
    "fixture_spec",
    "review_gate_checklist",
]
NEXT_REQUIRED_LADDER_STEPS = [
    "reviewed_output_schema",
    "local_reviewed_fixture",
    "internal_package_record",
    "coverage_summary_or_read_only_operator_surface",
    "customer_output_schema_gate",
    "internal_sample_output",
    "explicit_approval_or_hold_decision",
]

REQUIRED_EVIDENCE_FIELDS = [
    "wide_context_photo_or_permitted_visual_snapshot",
    "close_notice_or_required_element_photo_where_allowed",
    "timestamp_window",
    "visible_element_checklist",
    "source_type_observed_documented_or_heard",
    "obstruction_or_legibility_notes",
    "reviewed_limitations",
]

REQUIRED_OUTPUT_FIELDS = [
    "task_id_or_local_case_reference",
    "offer_type",
    "plain_language_status",
    "visible_elements_reviewed",
    "evidence_summary",
    "source_type_split",
    "obstruction_or_legibility_notes",
    "what_was_checked",
    "what_was_not_checked",
    "limitations_and_non_guarantees",
    "recommended_next_action",
    "operator_review_notice",
]

REVIEW_GATE_CHECKS = [
    "source_template_family_row_matches_compliance_desk",
    "evidence_contract_requires_context_and_close_notice_proof",
    "visible_element_checklist_is_required_but_not_treated_as_legal_compliance",
    "source_type_split_preserved_observed_documented_heard",
    "privacy_redaction_required_before_any_customer_language",
    "exact_gps_and_raw_metadata_blocked",
    "legal_advice_and_regulator_acceptance_claims_blocked",
    "operator_review_required_before_fixture_acceptance",
    "publication_customer_delivery_dispatch_reputation_and_worker_doctrine_blocked",
]

COMPLIANCE_SPECIFIC_BLOCKED_CLAIMS = [
    "legal_compliance",
    "official_inspection",
    "continuous_monitoring",
    "regulator_acceptance",
    "filing_success_ready",
    "city_relationship_or_influence",
    "worker_copyable_compliance_doctrine",
]

REQUIRED_BLOCKED_CLAIMS = [
    *TEMPLATE_BLOCKED_CLAIMS,
    *COMPLIANCE_SPECIFIC_BLOCKED_CLAIMS,
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "compliance_desk_customer_ready",
    "compliance_desk_catalog_ready",
    "compliance_desk_dispatch_ready",
    "compliance_desk_reputation_ready",
    "compliance_desk_worker_doctrine_ready",
}


def build_compliance_desk_fixture_review_gate(
    *, template: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the internal fixture spec and review-gate checklist.

    The returned artifact proves only that the first Compliance Desk adjacent-AAS
    fixture boundary exists. It does not prove reviewed fixtures, customer output,
    approval, publication, dispatch, reputation, or worker doctrine.
    """

    source_template = template or load_aas_minimum_ladder_template()
    family_row = _extract_compliance_family_row(source_template)

    gate = {
        "schema": COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SCHEMA,
        "gate_id": "execution_market.aas.compliance_desk.fixture_review_gate.2026_05_12",
        "scope": SCOPE,
        "package_family_id": PACKAGE_FAMILY_ID,
        "source_template_id": source_template["template_id"],
        "source_template_schema": source_template["schema"],
        "source_template_safe_claims_inherited": [
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM
        ],
        "safe_to_claim": [
            COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
            AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
        ],
        "do_not_claim_yet": _dedupe(
            [
                *REQUIRED_BLOCKED_CLAIMS,
                *source_template.get("do_not_claim_yet", []),
                *family_row.get("blocked_claims", []),
                *family_row.get("specific_blocked_claims", []),
            ]
        ),
        "ladder_boundary": {
            "required_full_ladder": list(REQUIRED_LADDER_STEPS),
            "covered_steps": list(COVERED_LADDER_STEPS),
            "next_required_steps_before_promotion": list(NEXT_REQUIRED_LADDER_STEPS),
            "promotion_allowed": False,
        },
        "fixture_spec": {
            "offer_id": OFFER_ID,
            "offer_label": "Visible Posting / Notice Compliance Snapshot",
            "family_label": family_row["label"],
            "caas_source_pattern": family_row["caas_source_pattern"],
            "source_caas_offer": "posting_compliance_check",
            "fixture_status": "spec_only_no_reviewed_fixture_yet",
            "operator_review_required": True,
            "customer_copy_changed": False,
            "phase_1_sellable_claim_allowed": False,
            "automation_claim_allowed": False,
            "required_evidence_fields": list(REQUIRED_EVIDENCE_FIELDS),
            "reviewed_output_schema_draft": {
                "status": "draft_internal_only_not_customer_output",
                "required_fields": list(REQUIRED_OUTPUT_FIELDS),
                "forbidden_fields": [
                    "exact_gps_coordinates",
                    "raw_metadata_blob",
                    "raw_transcript_as_authority",
                    "private_operator_context",
                    "guaranteed_compliance_language",
                    "legal_advice_or_legal_sufficiency",
                    "regulator_acceptance_claim",
                    "filing_success_claim",
                    "dispatch_instruction_or_assignment",
                    "erc8004_reputation_receipt",
                    "worker_copyable_compliance_doctrine",
                ],
            },
            "fixture_acceptance_gate": {
                "requires_local_reviewed_fixture": True,
                "requires_privacy_redaction_review": True,
                "requires_non_guarantee_language_review": True,
                "requires_operator_review_record": True,
                "preserves_safe_and_blocked_claims": True,
                "allows_customer_delivery": False,
                "allows_publication": False,
            },
        },
        "review_gate_checklist": [
            {
                "check_id": check,
                "required": True,
                "status": "pending_future_review",
                "blocks_promotion_until_passed": True,
            }
            for check in REVIEW_GATE_CHECKS
        ],
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "operator_instruction": (
            "Use this only as the Compliance Desk fixture boundary. The next valid "
            "step is a local reviewed fixture plus reviewed-output schema, not "
            "customer copy, catalog routing, dispatch, reputation, live memory, or "
            "worker-copyable compliance doctrine."
        ),
        "next_smallest_proof": (
            "Create one local reviewed Compliance Desk fixture for a visible posting "
            "snapshot that fills this evidence contract while keeping all promotion "
            "and customer/public readiness flags false."
        ),
    }
    _assert_gate_is_conservative(gate)
    return gate


def write_compliance_desk_fixture_review_gate(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Compliance Desk fixture review gate."""

    gate = build_compliance_desk_fixture_review_gate()
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_compliance_desk_fixture_review_gate(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Compliance Desk fixture review gate."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        gate = json.load(fh)
    if not isinstance(gate, dict):
        raise CityOpsContractError("Compliance Desk fixture review gate must be a JSON object")
    _assert_gate_is_conservative(gate)
    return gate


def _extract_compliance_family_row(template: dict[str, Any]) -> dict[str, Any]:
    if template.get("schema") != "city_ops.aas_minimum_ladder_template.v1":
        raise CityOpsContractError("Compliance Desk gate source template schema drift")
    if AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM not in template.get("safe_to_claim", []):
        raise CityOpsContractError("Compliance Desk gate source template safe claim missing")
    rows = template.get("families")
    if not isinstance(rows, list):
        raise CityOpsContractError("Compliance Desk gate source template missing family rows")
    matching = [row for row in rows if row.get("family_id") == PACKAGE_FAMILY_ID]
    if len(matching) != 1:
        raise CityOpsContractError("Compliance Desk family row missing from source template")
    row = matching[0]
    expected_evidence = set(REQUIRED_EVIDENCE_FIELDS)
    if not expected_evidence.issubset(set(row.get("required_evidence", []))):
        raise CityOpsContractError("Compliance Desk family row lost required evidence")
    if row.get("caas_source_pattern") != "posting_compliance_check":
        raise CityOpsContractError("Compliance Desk family row source pattern drift")
    return row


def _assert_gate_is_conservative(gate: dict[str, Any]) -> None:
    if gate.get("schema") != COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SCHEMA:
        raise CityOpsContractError("Compliance Desk fixture review gate schema drift")
    if gate.get("scope") != SCOPE:
        raise CityOpsContractError("Compliance Desk fixture review gate scope drift")
    if gate.get("package_family_id") != PACKAGE_FAMILY_ID:
        raise CityOpsContractError("Compliance Desk fixture review gate family drift")
    if set(gate.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS:
        raise CityOpsContractError("Compliance Desk fixture review gate has forbidden safe claims")

    missing_blocked = set(REQUIRED_BLOCKED_CLAIMS) - set(gate.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"Compliance Desk fixture review gate missing blocked claims: {sorted(missing_blocked)}"
        )

    ladder = gate.get("ladder_boundary", {})
    if ladder.get("covered_steps") != COVERED_LADDER_STEPS:
        raise CityOpsContractError("Compliance Desk fixture review gate covered steps drift")
    if ladder.get("next_required_steps_before_promotion") != NEXT_REQUIRED_LADDER_STEPS:
        raise CityOpsContractError("Compliance Desk fixture review gate next steps drift")
    if ladder.get("promotion_allowed") is not False:
        raise CityOpsContractError("Compliance Desk fixture review gate promoted readiness")

    readiness = gate.get("readiness", {})
    for flag in READINESS_FALSE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"Compliance Desk fixture review gate promoted readiness: {flag}")

    spec = gate.get("fixture_spec")
    if not isinstance(spec, dict):
        raise CityOpsContractError("Compliance Desk fixture spec must be an object")
    if spec.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("Compliance Desk fixture spec offer drift")
    if spec.get("operator_review_required") is not True:
        raise CityOpsContractError("Compliance Desk fixture spec must require operator review")
    for flag in (
        "customer_copy_changed",
        "phase_1_sellable_claim_allowed",
        "automation_claim_allowed",
    ):
        if spec.get(flag) is not False:
            raise CityOpsContractError(f"Compliance Desk fixture spec promoted {flag}")
    if not set(REQUIRED_EVIDENCE_FIELDS).issubset(set(spec.get("required_evidence_fields", []))):
        raise CityOpsContractError("Compliance Desk fixture spec lost required evidence")

    schema = spec.get("reviewed_output_schema_draft", {})
    if not set(REQUIRED_OUTPUT_FIELDS).issubset(set(schema.get("required_fields", []))):
        raise CityOpsContractError("Compliance Desk fixture spec lost output fields")
    forbidden_fields = set(schema.get("forbidden_fields", []))
    for field in (
        "exact_gps_coordinates",
        "raw_metadata_blob",
        "legal_advice_or_legal_sufficiency",
        "regulator_acceptance_claim",
        "worker_copyable_compliance_doctrine",
    ):
        if field not in forbidden_fields:
            raise CityOpsContractError("Compliance Desk fixture spec lost forbidden output fields")

    acceptance = spec.get("fixture_acceptance_gate", {})
    for required_true in (
        "requires_local_reviewed_fixture",
        "requires_privacy_redaction_review",
        "requires_non_guarantee_language_review",
        "requires_operator_review_record",
        "preserves_safe_and_blocked_claims",
    ):
        if acceptance.get(required_true) is not True:
            raise CityOpsContractError("Compliance Desk fixture acceptance gate lost required review")
    for required_false in ("allows_customer_delivery", "allows_publication"):
        if acceptance.get(required_false) is not False:
            raise CityOpsContractError("Compliance Desk fixture acceptance gate promoted readiness")

    checklist = gate.get("review_gate_checklist")
    if not isinstance(checklist, list) or len(checklist) != len(REVIEW_GATE_CHECKS):
        raise CityOpsContractError("Compliance Desk review gate checklist drift")
    check_ids = [item.get("check_id") for item in checklist if isinstance(item, dict)]
    if check_ids != REVIEW_GATE_CHECKS:
        raise CityOpsContractError("Compliance Desk review gate checklist order drift")
    for item in checklist:
        if item.get("required") is not True or item.get("blocks_promotion_until_passed") is not True:
            raise CityOpsContractError("Compliance Desk review gate checklist stopped blocking promotion")
        if item.get("status") != "pending_future_review":
            raise CityOpsContractError("Compliance Desk review gate checklist status drift")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
