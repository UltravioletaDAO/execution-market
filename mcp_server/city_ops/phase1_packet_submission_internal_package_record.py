"""Internal package record for Packet Submission Attempt.

This module creates the smallest proof-preserving internal package record for
Phase 1 Packet Submission Attempt. It deliberately does not create route
wrappers, customer copy, public catalog language, live Acontext readiness,
autonomous dispatch, ERC-8004 reputation, worker Skill DNA, legal/regulator
readiness, exact GPS/raw metadata exposure, or worker-copyable municipal
doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_review_output_schemas import OFFER_SPEC_DIR
from .phase1_reviewed_fixtures import (
    PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME,
    PACKET_SUBMISSION_ATTEMPT_FIXTURE_ID,
    PACKET_SUBMISSION_ATTEMPT_REVIEWED_FIXTURE_SAFE_CLAIM,
    load_packet_submission_attempt_reviewed_fixture,
)

PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SCHEMA = (
    "city_ops.phase1_packet_submission_internal_package_record.v1"
)
PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME = (
    "phase1_packet_submission_internal_package_record.json"
)
PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM = (
    "phase1_packet_submission_internal_package_record_landed"
)

PACKAGE_ID = "city_counter_ops.packet_submission_attempt.2026_05_10"
OFFER_ID = "packet_submission_attempt"
EXPECTED_PROOF_STATUS_LABEL = "local_anchor_supported_redirect_outdated_packet_only"

FORBIDDEN_PACKAGE_SAFE_CLAIMS = [
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "controlled_concierge_pilot_ready",
    "filing_success_ready",
    "broad_office_reuse_ready",
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


def build_phase1_packet_submission_internal_package_record(
    *,
    fixture_dir: str | Path | None = None,
    reviewed_fixture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the conservative internal package record from one reviewed fixture.

    The record intentionally stays an internal packaging artifact. It references
    the existing reviewed Packet Submission Attempt fixture and keeps safe and
    blocked claims adjacent so downstream handoffs cannot accidentally promote
    customer, dispatch, live-memory, reputation, GPS/metadata, or worker-doctrine
    claims.
    """

    source_fixture = reviewed_fixture or _load_packet_submission_fixture(fixture_dir)
    _assert_source_fixture_is_reviewed_packet_submission(source_fixture)

    safe_to_claim = _dedupe(
        [
            *source_fixture.get("safe_to_claim", []),
            PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_fixture.get("do_not_claim_yet", []),
            *REQUIRED_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    record = {
        "schema": PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SCHEMA,
        "package_id": PACKAGE_ID,
        "promotion_level": "controlled_concierge_pilot_candidate",
        "offer": OFFER_ID,
        "proof_status_label": source_fixture["reviewed_output"]["proof_status_label"],
        "reviewed_fixture_ids": [source_fixture["fixture_id"]],
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "source_reviewed_artifacts": [
            {
                "fixture_id": source_fixture["fixture_id"],
                "source_file": PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME,
                "source_schema": source_fixture["schema"],
                "outcome_status": source_fixture["reviewed_output"]["outcome_status"],
                "source_type": source_fixture["reviewed_output"]["source_type"],
                "follow_on_task_trigger": source_fixture["reviewed_output"][
                    "follow_on_task_trigger"
                ],
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
        "package_limitations": [
            "Tied only to the reviewed fixable non-redirect rejection fixture.",
            "Does not claim filing success, office reuse, city cooperation, legal sufficiency, or regulator acceptance.",
            "Requires operator review before any closure or pilot-facing use.",
        ],
        "next_smallest_proof": (
            "Keep this record internal. Do not draft customer copy or route wrappers; "
            "only stronger language after separate customer-schema, live Acontext, runtime, "
            "dispatch, reputation, GPS/privacy, and worker-doctrine gates pass."
        ),
    }
    _assert_package_record_is_conservative(record)
    return record


def write_phase1_packet_submission_internal_package_record(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the internal package record beside reviewed Phase 1 outputs."""

    record = build_phase1_packet_submission_internal_package_record(
        fixture_dir=fixture_dir
    )
    return _write_package_record(record, fixture_dir=fixture_dir)


def load_phase1_packet_submission_internal_package_record(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted internal package record."""

    path = _package_record_dir(fixture_dir) / PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        record = json.load(fh)
    if not isinstance(record, dict):
        raise CityOpsContractError("packet package record must be a JSON object")
    _assert_package_record_is_conservative(record)
    return record


def _write_package_record(
    record: dict[str, Any], *, fixture_dir: str | Path | None = None
) -> Path:
    _assert_package_record_is_conservative(record)
    base_dir = _package_record_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME
    # Keep insertion order so safe_to_claim and do_not_claim_yet remain adjacent
    # in the artifact as a reviewable safety contract.
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def _package_record_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _load_packet_submission_fixture(
    fixture_dir: str | Path | None = None,
) -> dict[str, Any]:
    try:
        return load_packet_submission_attempt_reviewed_fixture(fixture_dir=fixture_dir)
    except FileNotFoundError as exc:
        raise CityOpsContractError(
            "packet package record requires the reviewed Packet Submission Attempt fixture"
        ) from exc


def _assert_source_fixture_is_reviewed_packet_submission(fixture: dict[str, Any]) -> None:
    if fixture.get("fixture_id") != PACKET_SUBMISSION_ATTEMPT_FIXTURE_ID:
        raise CityOpsContractError("packet package record missing reviewed fixture")
    if fixture.get("offer_id") != OFFER_ID:
        raise CityOpsContractError("packet package record source must stay packet_submission_attempt")
    if fixture.get("safe_to_claim") != [PACKET_SUBMISSION_ATTEMPT_REVIEWED_FIXTURE_SAFE_CLAIM]:
        raise CityOpsContractError("packet package record source safe claim drift")
    reviewed_output = fixture.get("reviewed_output", {})
    if reviewed_output.get("operator_review_status") != "reviewed":
        raise CityOpsContractError("packet package record requires reviewed fixture output")
    if reviewed_output.get("proof_status_label") != EXPECTED_PROOF_STATUS_LABEL:
        raise CityOpsContractError("packet package record proof status drift")
    if reviewed_output.get("forbidden_claims_preserved") is not True:
        raise CityOpsContractError("packet package record requires preserved forbidden claims")
    scenario = fixture.get("scenario", {})
    if scenario.get("raw_transcript_used_as_authority") is not False:
        raise CityOpsContractError("packet package record cannot source raw transcripts")
    if scenario.get("unreviewed_memory_used") is not False:
        raise CityOpsContractError("packet package record cannot source unreviewed memory")
    if scenario.get("exact_gps_or_metadata_exposed") is not False:
        raise CityOpsContractError("packet package record cannot expose GPS or metadata")


def _assert_package_record_is_conservative(record: dict[str, Any]) -> None:
    if record.get("schema") != PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SCHEMA:
        raise CityOpsContractError("packet package record schema mismatch")
    if record.get("package_id") != PACKAGE_ID:
        raise CityOpsContractError("packet package record package_id drift")
    if record.get("promotion_level") != "controlled_concierge_pilot_candidate":
        raise CityOpsContractError("packet package record promotion level drift")
    if record.get("offer") != OFFER_ID:
        raise CityOpsContractError("packet package record offer drift")
    if record.get("proof_status_label") != EXPECTED_PROOF_STATUS_LABEL:
        raise CityOpsContractError("packet package record proof status drift")
    if record.get("reviewed_fixture_ids") != [PACKET_SUBMISSION_ATTEMPT_FIXTURE_ID]:
        raise CityOpsContractError("packet package record missing reviewed fixture")

    _assert_claim_boundaries(
        list(record.get("safe_to_claim", [])),
        list(record.get("do_not_claim_yet", [])),
    )

    promoted = [flag for flag in READINESS_FALSE_FLAGS if record.get(flag) is True]
    if promoted:
        raise CityOpsContractError(f"packet package record promoted readiness: {promoted}")
    missing_false = [flag for flag in READINESS_FALSE_FLAGS if record.get(flag) is not False]
    if missing_false:
        raise CityOpsContractError(
            f"packet package record readiness flags must be false: {missing_false}"
        )
    missing_true = [flag for flag in REQUIRED_TRUE_FLAGS if record.get(flag) is not True]
    if missing_true:
        raise CityOpsContractError(
            f"packet package record required flags drifted: {missing_true}"
        )

    internal_only = record.get("internal_only", {})
    if internal_only.get("uses_only_reviewed_fixture_artifacts") is not True:
        raise CityOpsContractError("packet package record must use reviewed artifacts only")
    for flag in [
        "customer_copy_changed",
        "public_catalog_changed",
        "route_wrapper_added",
        "raw_transcript_used",
        "unreviewed_memory_used",
        "private_operator_context_used",
    ]:
        if internal_only.get(flag) is not False:
            raise CityOpsContractError(f"packet package record internal-only drift: {flag}")

    source_artifacts = record.get("source_reviewed_artifacts")
    if not isinstance(source_artifacts, list) or len(source_artifacts) != 1:
        raise CityOpsContractError("packet package record requires one source artifact")
    source = source_artifacts[0]
    if source.get("fixture_id") != PACKET_SUBMISSION_ATTEMPT_FIXTURE_ID:
        raise CityOpsContractError("packet package record source fixture drift")
    if source.get("source_file") != PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME:
        raise CityOpsContractError("packet package record source file drift")


def _assert_claim_boundaries(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> None:
    if not safe_to_claim:
        raise CityOpsContractError("packet package record missing safe_to_claim")
    if not do_not_claim_yet:
        raise CityOpsContractError("packet package record missing do_not_claim_yet")
    forbidden_safe = sorted(set(safe_to_claim) & set(FORBIDDEN_PACKAGE_SAFE_CLAIMS))
    if forbidden_safe:
        raise CityOpsContractError(
            f"packet package record has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"packet package record claim overlap: {overlap}")
    missing_blocked = [claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet]
    if missing_blocked:
        raise CityOpsContractError(
            f"packet package record missing blocked claims: {missing_blocked}"
        )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
