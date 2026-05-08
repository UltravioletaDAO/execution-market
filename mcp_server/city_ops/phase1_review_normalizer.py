"""Phase 1 CaaS review normalizer draft.

This seam accepts a narrow operator/admin review form for one Phase 1
City-as-a-Service offer and emits the reviewed output shape enforced by
``phase1_review_output_schemas``. It is intentionally conservative: it does not
write municipal memory, does not publish customer copy, does not claim live
Acontext readiness, and does not close anything without explicit reviewed-output
fields.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_offer_fixture_specs import EXPECTED_PROOF_STATUS_BY_OFFER, REQUIRED_OFFER_IDS
from .phase1_review_output_schemas import (
    PHASE1_REVIEW_OUTPUT_SCHEMA_BUNDLE_FILENAME,
    OFFER_SPEC_DIR,
    build_phase1_review_output_schema_bundle,
    validate_phase1_review_output,
)

PHASE1_REVIEW_NORMALIZER_SUMMARY_SCHEMA = "city_ops.phase1_review_normalizer_summary.v1"
PHASE1_REVIEW_NORMALIZER_SUMMARY_FILENAME = "phase1_review_normalizer_summary.json"
PHASE1_REVIEW_NORMALIZER_SAFE_CLAIM = "phase_1_review_normalizer_draft_landed"

REVIEW_ONLY_DEFAULTS = {
    "operator_review_status": "reviewed",
    "forbidden_claims_preserved": True,
}

DO_NOT_CLAIM_YET = [
    "live_customer_schema_contract",
    "autonomous_review_closure",
    "durable_municipal_memory_write",
    "live_acontext_readiness",
    "autonomous_dispatch_readiness",
    "multi_jurisdiction_playbook_readiness",
    "worker_copyable_municipal_doctrine",
]


def normalize_phase1_review_output(
    review_form: dict[str, Any],
    *,
    bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize one operator-reviewed Phase 1 form into a reviewed output.

    The caller provides offer-specific review fields plus the shared outcome,
    source, evidence, and next-step fields. The normalizer stamps the narrow
    review-only fields when omitted, rejects attempts to broaden them, and then
    validates the result against the Phase 1 reviewed-output schema bundle.
    """

    if not isinstance(review_form, dict):
        raise CityOpsContractError("review_form must be an object")

    schema_bundle = bundle or build_phase1_review_output_schema_bundle()
    offer_id = review_form.get("offer") or review_form.get("offer_id")
    if offer_id not in REQUIRED_OFFER_IDS:
        raise CityOpsContractError(f"Unknown Phase 1 offer id: {offer_id}")

    schema = schema_bundle["schemas_by_offer"][offer_id]
    normalized = dict(review_form)
    normalized.pop("offer_id", None)
    normalized["offer"] = offer_id

    _apply_review_only_defaults(offer_id, normalized)
    _assert_required_fields_present(schema, normalized)
    _assert_required_fields_not_empty(schema, normalized)

    validate_phase1_review_output(offer_id, normalized, bundle=schema_bundle)

    return {
        field: normalized[field]
        for field in schema["required_fields"]
        if field in normalized
    }


def build_phase1_review_normalizer_summary(
    *, bundle: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Return a deterministic summary of the normalizer's closure guardrails."""

    schema_bundle = bundle or build_phase1_review_output_schema_bundle()
    required_fields_by_offer = {
        offer_id: schema_bundle["schemas_by_offer"][offer_id]["required_fields"]
        for offer_id in REQUIRED_OFFER_IDS
    }

    return {
        "schema": PHASE1_REVIEW_NORMALIZER_SUMMARY_SCHEMA,
        "summary_id": "caas_phase1_review_normalizer_summary_v0",
        "source_schema_bundle": PHASE1_REVIEW_OUTPUT_SCHEMA_BUNDLE_FILENAME,
        "offer_ids": list(REQUIRED_OFFER_IDS),
        "safe_to_claim": [PHASE1_REVIEW_NORMALIZER_SAFE_CLAIM],
        "do_not_claim_yet": list(DO_NOT_CLAIM_YET),
        "commercial_scope": {
            "operator_review_required": True,
            "concierge_only": True,
            "customer_copy_changed": False,
            "automation_claim_allowed": False,
            "live_transport_claim_allowed": False,
            "durable_memory_write_allowed": False,
        },
        "normalizer_behavior": {
            "accepts_operator_review_form": True,
            "emits_reviewed_output_schema": True,
            "stamps_operator_review_status_when_missing": "reviewed",
            "stamps_forbidden_claims_preserved_when_missing": True,
            "stamps_offer_specific_proof_status_label_when_missing": True,
            "rejects_missing_required_fields": True,
            "rejects_empty_required_strings": True,
            "rejects_broadened_proof_status": True,
            "rejects_unreviewed_operator_status": True,
            "does_not_write_memory": True,
        },
        "required_fields_by_offer": required_fields_by_offer,
        "next_daytime_task": (
            "Feed the normalizer with the first Counter Reality Check reviewed fixture, "
            "then only promote proof artifacts after the existing replay/promotion gates pass."
        ),
    }


def write_phase1_review_normalizer_summary(*, spec_dir: str | Path | None = None) -> Path:
    """Persist the deterministic normalizer summary next to the Phase 1 specs."""

    base_dir = OFFER_SPEC_DIR if spec_dir is None else Path(spec_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    summary = build_phase1_review_normalizer_summary()
    path = base_dir / PHASE1_REVIEW_NORMALIZER_SUMMARY_FILENAME
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _apply_review_only_defaults(offer_id: str, normalized: dict[str, Any]) -> None:
    for field, expected in REVIEW_ONLY_DEFAULTS.items():
        provided = normalized.get(field, expected)
        if provided != expected:
            raise CityOpsContractError(f"{field} must be {expected!r}")
        normalized[field] = expected

    expected_proof_status = EXPECTED_PROOF_STATUS_BY_OFFER[offer_id]
    provided_proof_status = normalized.get("proof_status_label", expected_proof_status)
    if provided_proof_status != expected_proof_status:
        raise CityOpsContractError(
            f"proof_status_label must stay {expected_proof_status!r}"
        )
    normalized["proof_status_label"] = expected_proof_status


def _assert_required_fields_present(schema: dict[str, Any], normalized: dict[str, Any]) -> None:
    missing = [field for field in schema["required_fields"] if field not in normalized]
    if missing:
        raise CityOpsContractError(f"review_form missing required fields: {missing}")


def _assert_required_fields_not_empty(schema: dict[str, Any], normalized: dict[str, Any]) -> None:
    empty = [
        field
        for field in schema["required_fields"]
        if isinstance(normalized.get(field), str) and not normalized[field].strip()
    ]
    if empty:
        raise CityOpsContractError(f"review_form has empty required fields: {empty}")
