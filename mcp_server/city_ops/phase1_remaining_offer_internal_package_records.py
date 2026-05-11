"""Internal package records for remaining Phase 1 City Counter Ops offers.

This module creates the conservative internal package records for Counter Reality
Check and Posting Compliance Check. The records deliberately stay internal:
no customer copy, public catalog, route wrapper, live Acontext readiness,
autonomous dispatch, ERC-8004 reputation, worker Skill DNA, exact GPS/raw
metadata exposure, legal/regulator readiness, or worker-copyable municipal
doctrine is promoted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .contracts import CityOpsContractError
from .phase1_review_output_schemas import OFFER_SPEC_DIR
from .phase1_reviewed_fixtures import (
    COUNTER_REALITY_CHECK_FIXTURE_FILENAME,
    COUNTER_REALITY_CHECK_FIXTURE_ID,
    COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
    POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME,
    POSTING_COMPLIANCE_CHECK_FIXTURE_ID,
    POSTING_COMPLIANCE_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
    load_counter_reality_check_reviewed_fixture,
    load_posting_compliance_check_reviewed_fixture,
)

PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SCHEMA = (
    "city_ops.phase1_counter_reality_check_internal_package_record.v1"
)
PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_FILENAME = (
    "phase1_counter_reality_check_internal_package_record.json"
)
PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM = (
    "phase1_counter_reality_check_internal_package_record_landed"
)

PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SCHEMA = (
    "city_ops.phase1_posting_compliance_internal_package_record.v1"
)
PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_FILENAME = (
    "phase1_posting_compliance_internal_package_record.json"
)
PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM = (
    "phase1_posting_compliance_internal_package_record_landed"
)

PROMOTION_LEVEL = "controlled_concierge_pilot_candidate"
EXPECTED_PROOF_STATUS_LABEL = "planning_supported_needs_first_fixture"

FORBIDDEN_PACKAGE_SAFE_CLAIMS = [
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_ready",
    "filing_success_ready",
    "broad_office_reuse_ready",
    "city_relationship_or_influence",
    "guaranteed_approval",
    "legal_sufficiency",
    "regulator_acceptance",
    "regulator_acceptance_ready",
    "live_acontext_ready",
    "live_acontext_readiness",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "runtime_parity_ready",
    "autonomous_dispatch_ready",
    "autonomous_dispatch_readiness",
    "dispatch_routing_ready",
    "dispatch_automation_ready",
    "erc8004_reputation_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "worker_copyable_municipal_doctrine",
    "worker-copyable municipal doctrine",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "exact_gps_or_metadata_exposure",
    "gps_metadata_exposure_ready",
]

REQUIRED_BLOCKED_CLAIMS = [
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_ready",
    "filing_success_ready",
    "broad_office_reuse_ready",
    "city_relationship_or_influence",
    "guaranteed_approval",
    "legal_sufficiency",
    "regulator_acceptance",
    "live_acontext_ready",
    "live_acontext_readiness",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "autonomous_dispatch_readiness",
    "dispatch_routing_ready",
    "erc8004_reputation_ready",
    "reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "worker_copyable_municipal_doctrine",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "exact_gps_or_metadata_exposure",
    "raw_metadata_exposure_allowed",
    "worker_copyable_municipal_doctrine_ready",
]

READINESS_FALSE_FLAGS = [
    "customer_output_schema_reviewed",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "worker_copyable_doctrine_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
]

REQUIRED_TRUE_FLAGS = [
    "operator_review_required_before_closure",
    "forbidden_claims_preserved",
]

_PACKAGE_SPECS: dict[str, dict[str, Any]] = {
    "counter_reality_check": {
        "schema": PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SCHEMA,
        "filename": PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_FILENAME,
        "safe_claim": PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
        "package_id": "city_counter_ops.counter_reality_check.2026_05_11",
        "fixture_id": COUNTER_REALITY_CHECK_FIXTURE_ID,
        "fixture_filename": COUNTER_REALITY_CHECK_FIXTURE_FILENAME,
        "source_safe_claim": COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
        "load_fixture": load_counter_reality_check_reviewed_fixture,
        "expected_outcome_status": "redirected",
        "expected_source_type": "mixed",
        "expected_follow_on_task_trigger": "office_redirect_follow_through",
        "source_privacy_phrase": "counter source must not expose private operator context",
        "limitations": [
            "Tied only to the reviewed synthetic redirect/outdated-packet fixture.",
            "Does not claim filing success, legal sufficiency, city influence, approval, or reusable office doctrine.",
            "Requires operator review before any closure or pilot-facing use.",
        ],
        "next_smallest_proof": (
            "Keep this record internal. It can support package coverage accounting only; "
            "customer-output schema review must remain a separate gate."
        ),
    },
    "posting_compliance_check": {
        "schema": PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SCHEMA,
        "filename": PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_FILENAME,
        "safe_claim": PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
        "package_id": "city_counter_ops.posting_compliance_check.2026_05_11",
        "fixture_id": POSTING_COMPLIANCE_CHECK_FIXTURE_ID,
        "fixture_filename": POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME,
        "source_safe_claim": POSTING_COMPLIANCE_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
        "load_fixture": load_posting_compliance_check_reviewed_fixture,
        "expected_outcome_status": "verified_partial",
        "expected_source_type": "observed",
        "expected_follow_on_task_trigger": "posting_recheck",
        "source_privacy_phrase": "posting source must not expose exact GPS or raw metadata",
        "limitations": [
            "Tied only to the reviewed synthetic partial-legibility posting fixture.",
            "Does not claim regulator acceptance, legal sufficiency, checklist completion, or approval.",
            "Requires privacy review before any customer-facing evidence language; exact GPS/raw metadata stays blocked.",
        ],
        "next_smallest_proof": (
            "Keep this record internal. It can support package coverage accounting only; "
            "customer-output schema review and GPS/raw-metadata privacy review must remain separate gates."
        ),
    },
}


def build_phase1_counter_reality_check_internal_package_record(
    *,
    fixture_dir: str | Path | None = None,
    reviewed_fixture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the conservative Counter Reality Check internal package record."""

    return _build_package_record(
        "counter_reality_check",
        fixture_dir=fixture_dir,
        reviewed_fixture=reviewed_fixture,
    )


def write_phase1_counter_reality_check_internal_package_record(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the Counter Reality Check internal package record."""

    record = build_phase1_counter_reality_check_internal_package_record(
        fixture_dir=fixture_dir
    )
    return _write_package_record(record, fixture_dir=fixture_dir)


def load_phase1_counter_reality_check_internal_package_record(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the Counter Reality Check internal package record."""

    return _load_package_record("counter_reality_check", fixture_dir=fixture_dir)


def build_phase1_posting_compliance_internal_package_record(
    *,
    fixture_dir: str | Path | None = None,
    reviewed_fixture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the conservative Posting Compliance Check internal package record."""

    return _build_package_record(
        "posting_compliance_check",
        fixture_dir=fixture_dir,
        reviewed_fixture=reviewed_fixture,
    )


def write_phase1_posting_compliance_internal_package_record(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the Posting Compliance Check internal package record."""

    record = build_phase1_posting_compliance_internal_package_record(
        fixture_dir=fixture_dir
    )
    return _write_package_record(record, fixture_dir=fixture_dir)


def load_phase1_posting_compliance_internal_package_record(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the Posting Compliance Check internal package record."""

    return _load_package_record("posting_compliance_check", fixture_dir=fixture_dir)


def _build_package_record(
    offer_id: str,
    *,
    fixture_dir: str | Path | None = None,
    reviewed_fixture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec = _PACKAGE_SPECS[offer_id]
    source_fixture = reviewed_fixture or _load_fixture(offer_id, fixture_dir)
    _assert_source_fixture_is_reviewed_offer(offer_id, source_fixture)

    safe_to_claim = _dedupe(
        [
            *source_fixture.get("safe_to_claim", []),
            spec["safe_claim"],
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_fixture.get("do_not_claim_yet", []),
            *REQUIRED_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(offer_id, safe_to_claim, do_not_claim_yet)

    reviewed_output = source_fixture["reviewed_output"]
    record = {
        "schema": spec["schema"],
        "package_id": spec["package_id"],
        "promotion_level": PROMOTION_LEVEL,
        "offer": offer_id,
        "proof_status_label": reviewed_output["proof_status_label"],
        "reviewed_fixture_ids": [source_fixture["fixture_id"]],
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "source_reviewed_artifacts": [
            {
                "fixture_id": source_fixture["fixture_id"],
                "source_file": spec["fixture_filename"],
                "source_schema": source_fixture["schema"],
                "outcome_status": reviewed_output["outcome_status"],
                "source_type": reviewed_output["source_type"],
                "follow_on_task_trigger": reviewed_output["follow_on_task_trigger"],
            }
        ],
        "customer_output_schema_reviewed": False,
        "operator_review_required_before_closure": True,
        "forbidden_claims_preserved": True,
        "live_acontext_ready": False,
        "runtime_parity_proven": False,
        "autonomous_dispatch_ready": False,
        "reputation_ready": False,
        "worker_copyable_doctrine_ready": False,
        "exact_gps_or_raw_metadata_exposure_allowed": False,
        "internal_only": {
            "customer_copy_changed": False,
            "public_catalog_changed": False,
            "route_wrapper_added": False,
            "uses_only_reviewed_fixture_artifacts": True,
            "raw_transcript_used": False,
            "unreviewed_memory_used": False,
            "private_operator_context_used": False,
        },
        "package_limitations": list(spec["limitations"]),
        "next_smallest_proof": spec["next_smallest_proof"],
    }
    _assert_package_record_is_conservative(offer_id, record)
    return record


def _write_package_record(
    record: dict[str, Any], *, fixture_dir: str | Path | None = None
) -> Path:
    offer_id = str(record.get("offer"))
    _assert_package_record_is_conservative(offer_id, record)
    base_dir = _package_record_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / _PACKAGE_SPECS[offer_id]["filename"]
    # Preserve insertion order so safe_to_claim and do_not_claim_yet stay adjacent.
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def _load_package_record(
    offer_id: str, *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    path = _package_record_dir(fixture_dir) / _PACKAGE_SPECS[offer_id]["filename"]
    with path.open("r", encoding="utf-8") as fh:
        record = json.load(fh)
    if not isinstance(record, dict):
        raise CityOpsContractError(f"{offer_id} package record must be a JSON object")
    _assert_package_record_is_conservative(offer_id, record)
    return record


def _package_record_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _load_fixture(offer_id: str, fixture_dir: str | Path | None = None) -> dict[str, Any]:
    loader: Callable[..., dict[str, Any]] = _PACKAGE_SPECS[offer_id]["load_fixture"]
    try:
        return loader(fixture_dir=fixture_dir)
    except FileNotFoundError as exc:
        raise CityOpsContractError(
            f"{offer_id} package record requires its reviewed fixture"
        ) from exc


def _assert_source_fixture_is_reviewed_offer(
    offer_id: str, fixture: dict[str, Any]
) -> None:
    spec = _PACKAGE_SPECS[offer_id]
    if fixture.get("fixture_id") != spec["fixture_id"]:
        raise CityOpsContractError(f"{offer_id} package record missing reviewed fixture")
    if fixture.get("offer_id") != offer_id:
        raise CityOpsContractError(f"{offer_id} package record source offer drift")
    if fixture.get("safe_to_claim") != [spec["source_safe_claim"]]:
        raise CityOpsContractError(f"{offer_id} package record source safe claim drift")

    reviewed_output = fixture.get("reviewed_output", {})
    if reviewed_output.get("operator_review_status") != "reviewed":
        raise CityOpsContractError(f"{offer_id} package record requires reviewed fixture output")
    if reviewed_output.get("proof_status_label") != EXPECTED_PROOF_STATUS_LABEL:
        raise CityOpsContractError(f"{offer_id} package record proof status drift")
    if reviewed_output.get("outcome_status") != spec["expected_outcome_status"]:
        raise CityOpsContractError(f"{offer_id} package record outcome drift")
    if reviewed_output.get("source_type") != spec["expected_source_type"]:
        raise CityOpsContractError(f"{offer_id} package record source type drift")
    if reviewed_output.get("follow_on_task_trigger") != spec["expected_follow_on_task_trigger"]:
        raise CityOpsContractError(f"{offer_id} package record follow-on trigger drift")
    if reviewed_output.get("forbidden_claims_preserved") is not True:
        raise CityOpsContractError(f"{offer_id} package record requires preserved forbidden claims")

    scenario = fixture.get("scenario", {})
    if scenario.get("raw_transcript_used_as_authority") is not False:
        raise CityOpsContractError(f"{offer_id} package record cannot source raw transcripts")
    if scenario.get("unreviewed_memory_used") is not False:
        raise CityOpsContractError(f"{offer_id} package record cannot source unreviewed memory")
    if scenario.get("exact_gps_or_metadata_exposed", False) is not False:
        raise CityOpsContractError(spec["source_privacy_phrase"])


def _assert_package_record_is_conservative(offer_id: str, record: dict[str, Any]) -> None:
    if offer_id not in _PACKAGE_SPECS:
        raise CityOpsContractError(f"unknown package record offer: {offer_id}")
    spec = _PACKAGE_SPECS[offer_id]
    if record.get("schema") != spec["schema"]:
        raise CityOpsContractError(f"{offer_id} package record schema mismatch")
    if record.get("package_id") != spec["package_id"]:
        raise CityOpsContractError(f"{offer_id} package record package_id drift")
    if record.get("promotion_level") != PROMOTION_LEVEL:
        raise CityOpsContractError(f"{offer_id} package record promotion level drift")
    if record.get("offer") != offer_id:
        raise CityOpsContractError(f"{offer_id} package record offer drift")
    if record.get("proof_status_label") != EXPECTED_PROOF_STATUS_LABEL:
        raise CityOpsContractError(f"{offer_id} package record proof status drift")
    if record.get("reviewed_fixture_ids") != [spec["fixture_id"]]:
        raise CityOpsContractError(f"{offer_id} package record missing reviewed fixture")

    _assert_claim_boundaries(
        offer_id,
        list(record.get("safe_to_claim", [])),
        list(record.get("do_not_claim_yet", [])),
    )

    promoted = [flag for flag in READINESS_FALSE_FLAGS if record.get(flag) is True]
    if promoted:
        raise CityOpsContractError(f"{offer_id} package record promoted readiness: {promoted}")
    missing_false = [flag for flag in READINESS_FALSE_FLAGS if record.get(flag) is not False]
    if missing_false:
        raise CityOpsContractError(
            f"{offer_id} package record readiness flags must be false: {missing_false}"
        )
    missing_true = [flag for flag in REQUIRED_TRUE_FLAGS if record.get(flag) is not True]
    if missing_true:
        raise CityOpsContractError(
            f"{offer_id} package record required flags drifted: {missing_true}"
        )

    internal_only = record.get("internal_only", {})
    if internal_only.get("uses_only_reviewed_fixture_artifacts") is not True:
        raise CityOpsContractError(f"{offer_id} package record must use reviewed artifacts only")
    for flag in [
        "customer_copy_changed",
        "public_catalog_changed",
        "route_wrapper_added",
        "raw_transcript_used",
        "unreviewed_memory_used",
        "private_operator_context_used",
    ]:
        if internal_only.get(flag) is not False:
            raise CityOpsContractError(f"{offer_id} package record internal-only drift: {flag}")

    source_artifacts = record.get("source_reviewed_artifacts")
    if not isinstance(source_artifacts, list) or len(source_artifacts) != 1:
        raise CityOpsContractError(f"{offer_id} package record requires one source artifact")
    source = source_artifacts[0]
    if source.get("fixture_id") != spec["fixture_id"]:
        raise CityOpsContractError(f"{offer_id} package record source fixture drift")
    if source.get("source_file") != spec["fixture_filename"]:
        raise CityOpsContractError(f"{offer_id} package record source file drift")


def _assert_claim_boundaries(
    offer_id: str, safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> None:
    if not safe_to_claim:
        raise CityOpsContractError(f"{offer_id} package record missing safe_to_claim")
    if not do_not_claim_yet:
        raise CityOpsContractError(f"{offer_id} package record missing do_not_claim_yet")
    forbidden_safe = sorted(set(safe_to_claim) & set(FORBIDDEN_PACKAGE_SAFE_CLAIMS))
    if forbidden_safe:
        raise CityOpsContractError(
            f"{offer_id} package record has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"{offer_id} package record claim overlap: {overlap}")
    missing_blocked = [claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet]
    if missing_blocked:
        raise CityOpsContractError(
            f"{offer_id} package record missing blocked claims: {missing_blocked}"
        )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
