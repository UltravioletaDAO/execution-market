"""Phase 1 CaaS offer fixture-spec guardrails.

This module turns the Phase 1 offer cards into deterministic fixture specs. It
is intentionally a planning/support seam: it does not create customer copy,
assert live Acontext readiness, broaden the city catalog, or make municipal
worker doctrine copyable. Its only job is to keep the first three CaaS offer
fixtures honest before real proof cases exist for every card.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError

PHASE1_OFFER_FIXTURE_SPEC_SCHEMA = "city_ops.phase1_offer_fixture_spec.v1"
PHASE1_OFFER_FIXTURE_SPEC_SUMMARY_SCHEMA = (
    "city_ops.phase1_offer_fixture_spec_summary.v1"
)
PHASE1_OFFER_FIXTURE_SPEC_SAFE_CLAIM = "phase_1_offer_fixture_specs_landed"

PHASE1_SPEC_DIRNAME = "phase1_offer_fixture_specs"
PHASE1_SUMMARY_FILENAME = "phase1_offer_fixture_spec_summary.json"

REQUIRED_OFFER_IDS = [
    "counter_reality_check",
    "packet_submission_attempt",
    "posting_compliance_check",
]

SPEC_FILES = [f"{offer_id}.json" for offer_id in REQUIRED_OFFER_IDS]

REQUIRED_REVIEWED_OUTPUT_FIELDS = [
    "source_type",
    "operator_review_status",
    "structured_next_step",
    "follow_on_task_trigger",
    "proof_status_label",
    "forbidden_claims_preserved",
]

REQUIRED_BLOCKED_CLAIMS = [
    "guaranteed_approval",
    "legal_sufficiency",
    "city_relationship_or_influence",
    "unlimited_retries",
    "broad_multi_office_base_order",
    "live_acontext_readiness",
    "autonomous_dispatch_readiness",
    "multi_jurisdiction_playbook_readiness",
    "worker_copyable_municipal_doctrine",
]

FORBIDDEN_SAFE_CLAIMS = [
    *REQUIRED_BLOCKED_CLAIMS,
    "acontext_sink_ready",
    "runtime_parity_proven",
    "acontext_live_transport_parity_landed",
    "autonomous_city_dispatch_ready",
    "worker-copyable municipal doctrine",
]

EXPECTED_PROOF_STATUS_BY_OFFER = {
    "counter_reality_check": "planning_supported_needs_first_fixture",
    "packet_submission_attempt": "local_anchor_supported_redirect_outdated_packet_only",
    "posting_compliance_check": "planning_supported_needs_first_fixture",
}

NEXT_FIXTURE_ORDER = [
    "counter_reality_check",
    "posting_compliance_check",
    "packet_submission_attempt_non_redirect",
]


def build_phase1_offer_fixture_spec_summary(
    *,
    spec_dir: str | Path | None = None,
    specs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate and summarize the Phase 1 offer fixture specs."""

    loaded_specs = specs or _load_phase1_specs(spec_dir)
    _assert_expected_specs(loaded_specs)

    validations = [
        _validate_spec(offer_id, spec) for offer_id, spec in loaded_specs.items()
    ]
    failed = [validation for validation in validations if validation["status"] != "passed"]
    if failed:
        raise CityOpsContractError(
            "Phase 1 offer fixture specs failed: "
            + "; ".join(
                f"{validation['offer_id']}:{validation['check']}={validation['status']} "
                f"errors={validation.get('errors', [])}"
                for validation in failed
            )
        )

    proof_status_by_offer = {
        offer_id: loaded_specs[offer_id]["proof_status_label"]
        for offer_id in REQUIRED_OFFER_IDS
    }
    output_fields_by_offer = {
        offer_id: loaded_specs[offer_id]["customer_output_schema_draft"][
            "required_fields"
        ]
        for offer_id in REQUIRED_OFFER_IDS
    }

    return {
        "schema": PHASE1_OFFER_FIXTURE_SPEC_SUMMARY_SCHEMA,
        "summary_id": "caas_phase1_offer_fixture_spec_summary_v0",
        "source_offer_pack": "CITY_AS_A_SERVICE_PHASE_1_OFFER_CARDS.md",
        "spec_count": len(loaded_specs),
        "offer_ids": list(REQUIRED_OFFER_IDS),
        "claim_boundaries": {
            "safe_to_claim": [PHASE1_OFFER_FIXTURE_SPEC_SAFE_CLAIM],
            "do_not_claim_yet": list(REQUIRED_BLOCKED_CLAIMS),
        },
        "commercial_scope": {
            "phase_1_sellable": True,
            "operator_review_required": True,
            "concierge_only": True,
            "one_metro_pilot": True,
            "automation_claim_allowed": False,
            "customer_copy_changed": False,
        },
        "proof_status_by_offer": proof_status_by_offer,
        "reviewed_output_fields_by_offer": output_fields_by_offer,
        "spec_validation_checks": validations,
        "next_fixture_order": list(NEXT_FIXTURE_ORDER),
        "next_daytime_task": (
            "Create the first Counter Reality Check proof fixture, then the first "
            "Posting Compliance Check proof fixture, before expanding front-door offers."
        ),
    }


def write_phase1_offer_fixture_spec_summary(
    *, spec_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic fixture-spec summary next to the specs."""

    base_dir = _default_spec_dir() if spec_dir is None else Path(spec_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    summary = build_phase1_offer_fixture_spec_summary(spec_dir=base_dir)
    path = base_dir / PHASE1_SUMMARY_FILENAME
    path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _load_phase1_specs(spec_dir: str | Path | None = None) -> dict[str, dict[str, Any]]:
    base_dir = _default_spec_dir() if spec_dir is None else Path(spec_dir)
    return {
        offer_id: _load_json(base_dir / filename)
        for offer_id, filename in zip(REQUIRED_OFFER_IDS, SPEC_FILES)
    }


def _default_spec_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / PHASE1_SPEC_DIRNAME


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise CityOpsContractError(f"{path.name} must contain a JSON object")
    return value


def _assert_expected_specs(specs: dict[str, dict[str, Any]]) -> None:
    missing = [offer_id for offer_id in REQUIRED_OFFER_IDS if offer_id not in specs]
    extra = [offer_id for offer_id in specs if offer_id not in REQUIRED_OFFER_IDS]
    if missing or extra:
        raise CityOpsContractError(
            f"Phase 1 fixture spec set mismatch: missing={missing}, extra={extra}"
        )


def _validate_spec(offer_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if spec.get("schema") != PHASE1_OFFER_FIXTURE_SPEC_SCHEMA:
        errors.append("schema mismatch")
    if spec.get("offer_id") != offer_id:
        errors.append("offer_id mismatch")
    if spec.get("phase") != "phase_1":
        errors.append("phase must be phase_1")
    if spec.get("operator_review_required") is not True:
        errors.append("operator_review_required must be true")
    if spec.get("phase_1_sellable") is not True:
        errors.append("phase_1_sellable must be true")
    if spec.get("automation_claim_allowed") is not False:
        errors.append("automation_claim_allowed must be false")

    expected_proof_status = EXPECTED_PROOF_STATUS_BY_OFFER[offer_id]
    if spec.get("proof_status_label") != expected_proof_status:
        errors.append(
            f"proof_status_label must stay {expected_proof_status!r}"
        )

    safe_to_claim = _string_list(spec, "safe_to_claim", errors)
    do_not_claim_yet = _string_list(spec, "do_not_claim_yet", errors)
    forbidden_customer_claims = _string_list(spec, "forbidden_customer_claims", errors)

    missing_blocked = [
        claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet
    ]
    if missing_blocked:
        errors.append(f"missing do_not_claim_yet claims: {missing_blocked}")

    missing_forbidden = [
        claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in forbidden_customer_claims
    ]
    if missing_forbidden:
        errors.append(f"missing forbidden_customer_claims: {missing_forbidden}")

    unsafe_safe_claims = [
        claim for claim in FORBIDDEN_SAFE_CLAIMS if claim in safe_to_claim
    ]
    if unsafe_safe_claims:
        errors.append(f"forbidden claims appeared as safe_to_claim: {unsafe_safe_claims}")

    output_schema = spec.get("customer_output_schema_draft")
    if not isinstance(output_schema, dict):
        errors.append("customer_output_schema_draft must be an object")
        required_fields: list[str] = []
    else:
        required_fields = output_schema.get("required_fields", [])
        if not isinstance(required_fields, list):
            errors.append("customer_output_schema_draft.required_fields must be a list")
            required_fields = []

    missing_output_fields = [
        field for field in REQUIRED_REVIEWED_OUTPUT_FIELDS if field not in required_fields
    ]
    if missing_output_fields:
        errors.append(f"missing reviewed output fields: {missing_output_fields}")

    if (
        spec.get("fixture_acceptance_gate", {}).get(
            "preserves_safe_and_blocked_claims"
        )
        is not True
    ):
        errors.append("fixture_acceptance_gate must preserve safe and blocked claims")

    if errors:
        return {
            "offer_id": offer_id,
            "check": "phase1_offer_fixture_spec_contract",
            "status": "failed",
            "errors": errors,
        }

    return {
        "offer_id": offer_id,
        "check": "phase1_offer_fixture_spec_contract",
        "status": "passed",
        "proof_status_label": spec["proof_status_label"],
        "required_output_fields": required_fields,
    }


def _string_list(spec: dict[str, Any], key: str, errors: list[str]) -> list[str]:
    value = spec.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{key} must be a list of strings")
        return []
    return value
