"""Phase 1 CaaS reviewed-output schema drafts.

This seam turns the Phase 1 offer fixture specs into deterministic reviewed-output
schema drafts. It is deliberately conservative: the schemas are internal review
contracts for fixture/proof work, not live customer-copy promises, not Acontext
readiness, and not autonomous municipal dispatch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_offer_fixture_specs import (
    EXPECTED_PROOF_STATUS_BY_OFFER,
    PHASE1_SUMMARY_FILENAME,
    REQUIRED_BLOCKED_CLAIMS,
    REQUIRED_OFFER_IDS,
    REQUIRED_REVIEWED_OUTPUT_FIELDS,
    build_phase1_offer_fixture_spec_summary,
)

PHASE1_REVIEW_OUTPUT_SCHEMA = "city_ops.phase1_review_output_schema.v1"
PHASE1_REVIEW_OUTPUT_SCHEMA_BUNDLE_SCHEMA = (
    "city_ops.phase1_review_output_schema_bundle.v1"
)
PHASE1_REVIEW_OUTPUT_SCHEMA_BUNDLE_FILENAME = (
    "phase1_review_output_schema_bundle.json"
)
PHASE1_REVIEW_OUTPUT_SCHEMA_SAFE_CLAIM = (
    "phase_1_review_output_schema_drafts_landed"
)

REQUIRED_SHARED_REVIEW_OUTPUT_FIELDS = [
    "offer",
    "outcome_status",
    "source_type",
    "evidence_summary",
    "operator_review_status",
    "structured_next_step",
    "follow_on_task_trigger",
    "proof_status_label",
    "forbidden_claims_preserved",
]

REQUIRED_SCHEMA_GUARDRAILS = [
    "operator_review_required",
    "no_customer_copy_change",
    "no_automation_claim",
    "preserve_forbidden_claims",
    "proof_status_must_match_offer_spec",
]

BASE_FIELD_CONTRACTS = {
    "offer": {
        "type": "string",
        "meaning": "The Phase 1 offer id that produced the reviewed output.",
    },
    "outcome_status": {
        "type": "enum",
        "meaning": "Reviewed municipal outcome classification from the offer spec.",
    },
    "source_type": {
        "type": "enum",
        "meaning": "Explicit separation of observed, documented, staff-heard, customer-supplied, or mixed source.",
    },
    "evidence_summary": {
        "type": "array[string]",
        "meaning": "Concise reviewed evidence notes; never raw municipal authority by itself.",
    },
    "operator_review_status": {
        "type": "enum",
        "meaning": "Phase 1 outputs must be operator reviewed before closure.",
    },
    "structured_next_step": {
        "type": "string",
        "meaning": "Operational next step, not legal advice or guaranteed approval path.",
    },
    "follow_on_task_trigger": {
        "type": "enum|null",
        "meaning": "Explicit add-on/new-task trigger; no silent extra retry bundled into the base order.",
    },
    "proof_status_label": {
        "type": "enum",
        "meaning": "Narrow proof label inherited from the fixture spec.",
    },
    "forbidden_claims_preserved": {
        "type": "boolean:true",
        "meaning": "Reviewer asserts blocked customer/product claims were not upgraded.",
    },
}

OFFER_SPEC_DIR = Path(__file__).resolve().parent / "fixtures" / "phase1_offer_fixture_specs"


def build_phase1_review_output_schema_bundle(
    *,
    spec_dir: str | Path | None = None,
    specs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build and validate reviewed-output schema drafts for all Phase 1 offers."""

    base_dir = OFFER_SPEC_DIR if spec_dir is None else Path(spec_dir)
    loaded_specs = specs or _load_phase1_specs(base_dir)

    # Reuse the fixture-spec validator first so this seam cannot broaden the pack.
    spec_summary = build_phase1_offer_fixture_spec_summary(
        spec_dir=base_dir if specs is None else None,
        specs=loaded_specs,
    )

    schemas_by_offer = {
        offer_id: _build_schema_for_offer(offer_id, loaded_specs[offer_id])
        for offer_id in REQUIRED_OFFER_IDS
    }

    validations = [
        _validate_schema_against_spec(offer_id, schema, loaded_specs[offer_id])
        for offer_id, schema in schemas_by_offer.items()
    ]
    failed = [validation for validation in validations if validation["status"] != "passed"]
    if failed:
        raise CityOpsContractError(
            "Phase 1 reviewed-output schemas failed: "
            + "; ".join(
                f"{validation['offer_id']}:{validation['check']}={validation['status']} "
                f"errors={validation.get('errors', [])}"
                for validation in failed
            )
        )

    return {
        "schema": PHASE1_REVIEW_OUTPUT_SCHEMA_BUNDLE_SCHEMA,
        "bundle_id": "caas_phase1_review_output_schema_bundle_v0",
        "source_offer_pack": spec_summary["source_offer_pack"],
        "source_fixture_spec_summary": PHASE1_SUMMARY_FILENAME,
        "offer_ids": list(REQUIRED_OFFER_IDS),
        "safe_to_claim": [PHASE1_REVIEW_OUTPUT_SCHEMA_SAFE_CLAIM],
        "do_not_claim_yet": _unique_strings(
            [
                *REQUIRED_BLOCKED_CLAIMS,
                "review_normalizer_landed",
                "live_customer_schema_contract",
                "autonomous_review_closure",
                "live_acontext_readiness",
            ]
        ),
        "commercial_scope": {
            "operator_review_required": True,
            "concierge_only": True,
            "automation_claim_allowed": False,
            "customer_copy_changed": False,
            "live_transport_claim_allowed": False,
        },
        "shared_required_fields": list(REQUIRED_SHARED_REVIEW_OUTPUT_FIELDS),
        "schemas_by_offer": schemas_by_offer,
        "schema_validation_checks": validations,
        "next_daytime_task": (
            "Wire these reviewed-output schemas into the first review normalizer draft "
            "before promoting any Phase 1 offer to live customer-copy contract."
        ),
    }


def write_phase1_review_output_schema_bundle(
    *, spec_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic reviewed-output schema bundle next to the specs."""

    base_dir = OFFER_SPEC_DIR if spec_dir is None else Path(spec_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    bundle = build_phase1_review_output_schema_bundle(spec_dir=base_dir)
    path = base_dir / PHASE1_REVIEW_OUTPUT_SCHEMA_BUNDLE_FILENAME
    path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def validate_phase1_review_output(
    offer_id: str,
    reviewed_output: dict[str, Any],
    *,
    bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate one reviewed output against the conservative Phase 1 draft."""

    schema_bundle = bundle or build_phase1_review_output_schema_bundle()
    schemas_by_offer = schema_bundle.get("schemas_by_offer", {})
    if offer_id not in schemas_by_offer:
        raise CityOpsContractError(f"Unknown Phase 1 offer id: {offer_id}")
    schema = schemas_by_offer[offer_id]

    errors: list[str] = []
    if not isinstance(reviewed_output, dict):
        raise CityOpsContractError("reviewed_output must be an object")

    missing = [field for field in schema["required_fields"] if field not in reviewed_output]
    if missing:
        errors.append(f"missing required fields: {missing}")

    if reviewed_output.get("offer") != offer_id:
        errors.append("offer must match schema offer_id")

    enum_constraints = schema["enum_constraints"]
    _assert_value_allowed(
        reviewed_output,
        "outcome_status",
        enum_constraints["outcome_status"],
        errors,
    )
    _assert_value_allowed(
        reviewed_output,
        "source_type",
        enum_constraints["source_type"],
        errors,
    )
    _assert_value_allowed(
        reviewed_output,
        "operator_review_status",
        enum_constraints["operator_review_status"],
        errors,
    )
    _assert_value_allowed(
        reviewed_output,
        "follow_on_task_trigger",
        enum_constraints["follow_on_task_trigger"],
        errors,
    )
    _assert_value_allowed(
        reviewed_output,
        "proof_status_label",
        enum_constraints["proof_status_label"],
        errors,
    )

    if reviewed_output.get("forbidden_claims_preserved") is not True:
        errors.append("forbidden_claims_preserved must be true")

    evidence_summary = reviewed_output.get("evidence_summary")
    if not isinstance(evidence_summary, list) or not all(
        isinstance(item, str) and item.strip() for item in evidence_summary
    ):
        errors.append("evidence_summary must be a non-empty list of strings")

    next_step = reviewed_output.get("structured_next_step")
    if not isinstance(next_step, str) or not next_step.strip():
        errors.append("structured_next_step must be a non-empty string")

    if errors:
        raise CityOpsContractError(
            f"Phase 1 reviewed output failed for {offer_id}: {errors}"
        )

    return {
        "offer_id": offer_id,
        "check": "phase1_review_output_schema_contract",
        "status": "passed",
        "schema_id": schema["schema_id"],
    }


def _build_schema_for_offer(offer_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    output_schema = spec.get("customer_output_schema_draft", {})
    required_fields = list(output_schema.get("required_fields", []))

    # Keep the offer-card-specific fields, but force the cross-offer review seam in.
    for required_field in REQUIRED_SHARED_REVIEW_OUTPUT_FIELDS:
        if required_field not in required_fields:
            required_fields.append(required_field)
    for required_field in REQUIRED_REVIEWED_OUTPUT_FIELDS:
        if required_field not in required_fields:
            required_fields.append(required_field)

    follow_on_options = [
        None if trigger == "null" else trigger
        for trigger in spec.get("follow_on_task_triggers", [])
    ]
    if None not in follow_on_options:
        follow_on_options.append(None)

    return {
        "schema": PHASE1_REVIEW_OUTPUT_SCHEMA,
        "schema_id": f"caas_phase1_{offer_id}_review_output_schema_v0",
        "offer_id": offer_id,
        "required_fields": required_fields,
        "field_contracts": {
            field: BASE_FIELD_CONTRACTS[field]
            for field in REQUIRED_SHARED_REVIEW_OUTPUT_FIELDS
        },
        "enum_constraints": {
            "outcome_status": list(spec.get("outcome_status_options", [])),
            "source_type": list(spec.get("source_type_options", [])),
            "operator_review_status": ["reviewed"],
            "follow_on_task_trigger": follow_on_options,
            "proof_status_label": [EXPECTED_PROOF_STATUS_BY_OFFER[offer_id]],
        },
        "boolean_constraints": {"forbidden_claims_preserved": True},
        "guardrails": list(REQUIRED_SCHEMA_GUARDRAILS),
        "forbidden_customer_claims": list(REQUIRED_BLOCKED_CLAIMS),
        "customer_copy_changed": False,
        "automation_claim_allowed": False,
        "operator_review_required": True,
        "proof_status_label": EXPECTED_PROOF_STATUS_BY_OFFER[offer_id],
    }


def _validate_schema_against_spec(
    offer_id: str, schema: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []

    if schema.get("schema") != PHASE1_REVIEW_OUTPUT_SCHEMA:
        errors.append("schema mismatch")
    if schema.get("offer_id") != offer_id:
        errors.append("offer_id mismatch")
    if schema.get("operator_review_required") is not True:
        errors.append("operator_review_required must be true")
    if schema.get("automation_claim_allowed") is not False:
        errors.append("automation_claim_allowed must be false")
    if schema.get("customer_copy_changed") is not False:
        errors.append("customer_copy_changed must be false")
    if schema.get("proof_status_label") != EXPECTED_PROOF_STATUS_BY_OFFER[offer_id]:
        errors.append("proof_status_label broadened or mismatched")

    required_fields = schema.get("required_fields", [])
    if not isinstance(required_fields, list):
        errors.append("required_fields must be a list")
        required_fields = []

    missing_shared = [
        field for field in REQUIRED_SHARED_REVIEW_OUTPUT_FIELDS if field not in required_fields
    ]
    if missing_shared:
        errors.append(f"missing shared required fields: {missing_shared}")

    missing_reviewed = [
        field for field in REQUIRED_REVIEWED_OUTPUT_FIELDS if field not in required_fields
    ]
    if missing_reviewed:
        errors.append(f"missing reviewed output fields: {missing_reviewed}")

    spec_required = spec.get("customer_output_schema_draft", {}).get("required_fields", [])
    missing_from_spec = [field for field in spec_required if field not in required_fields]
    if missing_from_spec:
        errors.append(f"dropped spec-required fields: {missing_from_spec}")

    enum_constraints = schema.get("enum_constraints", {})
    if enum_constraints.get("outcome_status") != spec.get("outcome_status_options"):
        errors.append("outcome_status options must match fixture spec")
    if enum_constraints.get("source_type") != spec.get("source_type_options"):
        errors.append("source_type options must match fixture spec")
    if enum_constraints.get("operator_review_status") != ["reviewed"]:
        errors.append("operator_review_status must only allow reviewed")
    if enum_constraints.get("proof_status_label") != [
        EXPECTED_PROOF_STATUS_BY_OFFER[offer_id]
    ]:
        errors.append("proof_status_label enum must stay narrow")

    guardrails = schema.get("guardrails", [])
    missing_guardrails = [
        guardrail for guardrail in REQUIRED_SCHEMA_GUARDRAILS if guardrail not in guardrails
    ]
    if missing_guardrails:
        errors.append(f"missing guardrails: {missing_guardrails}")

    missing_forbidden = [
        claim
        for claim in REQUIRED_BLOCKED_CLAIMS
        if claim not in schema.get("forbidden_customer_claims", [])
    ]
    if missing_forbidden:
        errors.append(f"missing forbidden claims: {missing_forbidden}")

    if errors:
        return {
            "offer_id": offer_id,
            "check": "phase1_review_output_schema_contract",
            "status": "failed",
            "errors": errors,
        }

    return {
        "offer_id": offer_id,
        "check": "phase1_review_output_schema_contract",
        "status": "passed",
        "required_field_count": len(required_fields),
        "guardrail_count": len(schema["guardrails"]),
    }


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return unique


def _load_phase1_specs(spec_dir: Path) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for offer_id in REQUIRED_OFFER_IDS:
        path = spec_dir / f"{offer_id}.json"
        with path.open("r", encoding="utf-8") as fh:
            value = json.load(fh)
        if not isinstance(value, dict):
            raise CityOpsContractError(f"{path.name} must contain a JSON object")
        specs[offer_id] = value
    return specs


def _assert_value_allowed(
    reviewed_output: dict[str, Any],
    field: str,
    allowed: list[Any],
    errors: list[str],
) -> None:
    if field not in reviewed_output:
        return
    value = reviewed_output.get(field)
    if value not in allowed:
        errors.append(f"{field} must be one of {allowed!r}")
