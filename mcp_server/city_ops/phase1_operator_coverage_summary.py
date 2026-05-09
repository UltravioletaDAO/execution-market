"""Read-only operator/admin coverage summary for Phase 1 CaaS fixtures.

This module renders the already-reviewed Phase 1 fixture registry into a tiny
operator coverage surface.  It is intentionally read-only and claim-conservative:
it counts reviewed fixtures, keeps ``safe_to_claim`` and ``do_not_claim_yet``
adjacent, and refuses to promote customer copy, dispatch automation, live
Acontext, ERC-8004 reputation, worker Skill DNA, legal/regulator sufficiency,
GPS/metadata exposure, or worker-copyable municipal doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_review_output_schemas import OFFER_SPEC_DIR
from .phase1_reviewed_fixtures import (
    PHASE1_REVIEWED_FIXTURE_REGISTRY_SCHEMA,
    load_phase1_reviewed_fixture_registry_summary,
)

PHASE1_OPERATOR_COVERAGE_SUMMARY_SCHEMA = "city_ops.phase1_operator_coverage_summary.v1"
PHASE1_OPERATOR_COVERAGE_SUMMARY_SAFE_CLAIM = "phase1_operator_coverage_summary_landed"
PHASE1_OPERATOR_COVERAGE_ARTIFACT_SAFE_CLAIM = "phase1_operator_coverage_artifact_landed"
PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME = "phase1_operator_coverage_summary.json"

# Claims this tiny operator/admin surface must never move into safe_to_claim.
FORBIDDEN_OPERATOR_COVERAGE_SAFE_CLAIMS = [
    "customer_copy_ready",
    "operator_ui_ready",
    "dispatch_routing_ready",
    "dispatch_automation_ready",
    "autonomous_dispatch_readiness",
    "autonomous_dispatch_ready",
    "live_acontext_readiness",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "legal_sufficiency",
    "regulator_acceptance",
    "regulator_acceptance_ready",
    "exact_gps_or_metadata_exposure",
    "gps_metadata_exposure_ready",
    "worker_copyable_municipal_doctrine",
    "worker-copyable municipal doctrine",
]

# Some blocked claims are explicit summary-only guardrails, even if the registry
# used adjacent equivalent names for the same risk.
REQUIRED_OPERATOR_BLOCKED_CLAIMS = [
    "customer_copy_ready",
    "operator_ui_ready",
    "dispatch_routing_ready",
    "dispatch_automation_ready",
    "live_acontext_readiness",
    "acontext_sink_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "legal_sufficiency",
    "regulator_acceptance",
    "exact_gps_or_metadata_exposure",
    "worker_copyable_municipal_doctrine",
]

READINESS_FALSE_FLAGS = [
    "customer_copy_ready",
    "dispatch_automation_ready",
    "live_acontext_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "legal_sufficiency_claim_allowed",
    "regulator_acceptance_claim_allowed",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_municipal_doctrine_ready",
]


def build_phase1_operator_coverage_summary(
    *,
    fixture_dir: str | Path | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a tiny read-only operator coverage summary from the registry.

    The summary is for internal operator/admin observability only.  It does not
    reinterpret the reviewed fixtures, does not write memory or transport state,
    and does not create customer-copy, dispatch, legal, regulator, reputation,
    worker-skill, or GPS/metadata readiness.
    """

    source_registry = registry or load_phase1_reviewed_fixture_registry_summary(
        fixture_dir=fixture_dir
    )
    _assert_registry_is_safe_source(source_registry)

    inherited_safe = list(source_registry.get("safe_to_claim", []))
    safe_to_claim = _dedupe(
        [
            *inherited_safe,
            PHASE1_OPERATOR_COVERAGE_SUMMARY_SAFE_CLAIM,
            PHASE1_OPERATOR_COVERAGE_ARTIFACT_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_registry.get("do_not_claim_yet", []),
            *REQUIRED_OPERATOR_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    coverage_rows = [
        _coverage_row(offer_id, row)
        for offer_id, row in sorted(source_registry["coverage_by_offer"].items())
    ]

    summary = {
        "schema": PHASE1_OPERATOR_COVERAGE_SUMMARY_SCHEMA,
        "summary_id": f"operator_coverage:{source_registry['registry_id']}",
        "source_registry_id": source_registry["registry_id"],
        "derived_from": {
            "read_only": True,
            "source_artifact": "phase1_reviewed_fixture_registry_summary.json",
            "source_schema": source_registry["schema"],
            "source_reviewed_outputs": list(source_registry["source_reviewed_outputs"]),
            "forbidden_sources": [
                "raw_transcript",
                "unreviewed_memory",
                "freeform_worker_chat",
                "private_operator_context",
                "live_acontext_transport",
                "gps_or_metadata_payloads",
            ],
            "writes_customer_copy": False,
            "writes_municipal_memory": False,
            "writes_live_acontext": False,
            "enables_dispatch_automation": False,
            "publishes_worker_doctrine": False,
        },
        "coverage_totals": {
            "reviewed_fixture_count": source_registry["total_reviewed_fixtures"],
            "offer_count": len(source_registry["offer_ids"]),
            "all_phase1_offers_have_reviewed_fixture": source_registry[
                "operator_observability"
            ]["all_phase1_offers_have_reviewed_fixture"],
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "coverage_by_offer": coverage_rows,
        "readiness": {flag: False for flag in READINESS_FALSE_FLAGS},
        "summary_verdict": "operator_coverage_summary_landed_read_only_not_customer_ready",
        "next_smallest_proof": (
            "Use this persisted internal operator/admin artifact only through thin read-only "
            "surfaces. Customer copy, dispatch "
            "automation, live Acontext, ERC-8004 reputation, worker Skill DNA, legal/regulator "
            "claims, GPS/metadata exposure, and worker-copyable municipal doctrine remain blocked."
        ),
    }
    _assert_summary_is_conservative(summary)
    return summary


def write_phase1_operator_coverage_summary(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the generated operator coverage summary as a local artifact.

    Persistence is intentionally local and read-only for downstream consumers:
    no customer copy, municipal memory, live Acontext, dispatch automation,
    reputation, worker Skill DNA, legal/regulator readiness, GPS/metadata, or
    worker-copyable doctrine is promoted by writing this file.
    """

    summary = build_phase1_operator_coverage_summary(fixture_dir=fixture_dir)
    return _write_operator_coverage_summary(summary, fixture_dir=fixture_dir)


def load_phase1_operator_coverage_summary(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted operator coverage summary artifact."""

    path = _operator_coverage_summary_dir(fixture_dir) / PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        summary = json.load(fh)
    if not isinstance(summary, dict):
        raise CityOpsContractError("operator coverage summary artifact must be a JSON object")
    _assert_summary_is_conservative(summary)
    return summary


def _write_operator_coverage_summary(
    summary: dict[str, Any], *, fixture_dir: str | Path | None = None
) -> Path:
    _assert_summary_is_conservative(summary)
    base_dir = _operator_coverage_summary_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _operator_coverage_summary_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _coverage_row(offer_id: str, row: dict[str, Any]) -> dict[str, Any]:
    safe_to_claim = list(row.get("safe_to_claim", []))
    do_not_claim_yet = list(row.get("do_not_claim_yet", []))
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)
    for flag in [
        "customer_copy_changed",
        "durable_municipal_memory_write_performed",
        "acontext_write_performed",
        "autonomous_dispatch_enabled",
    ]:
        if row.get(flag) is not False:
            raise CityOpsContractError(
                f"operator coverage row overclaims {flag}: {offer_id}"
            )

    return {
        "offer_id": offer_id,
        "fixture_id": row["fixture_id"],
        "source_file": row["source_file"],
        "outcome_status": row["outcome_status"],
        "source_type": row["source_type"],
        "follow_on_task_trigger": row["follow_on_task_trigger"],
        "proof_status_label": row["proof_status_label"],
        "claims": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "promoted_readiness": {
            "customer_copy_ready": False,
            "dispatch_automation_ready": False,
            "live_acontext_ready": False,
            "legal_or_regulator_ready": False,
            "gps_or_metadata_exposure_allowed": False,
            "worker_copyable_municipal_doctrine_ready": False,
        },
    }


def _assert_registry_is_safe_source(registry: dict[str, Any]) -> None:
    if registry.get("schema") != PHASE1_REVIEWED_FIXTURE_REGISTRY_SCHEMA:
        raise CityOpsContractError("operator coverage summary expected reviewed registry schema")
    coverage = registry.get("coverage_by_offer")
    if not isinstance(coverage, dict) or not coverage:
        raise CityOpsContractError("operator coverage summary requires coverage_by_offer")
    if registry.get("total_reviewed_fixtures") != len(coverage):
        raise CityOpsContractError("operator coverage summary fixture count drift")
    observability = registry.get("operator_observability", {})
    if observability.get("safe_and_blocked_claims_travel_together") is not True:
        raise CityOpsContractError("operator coverage summary requires adjacent claim lists")
    if observability.get("exact_gps_or_metadata_exposed") is not False:
        raise CityOpsContractError("operator coverage summary cannot expose GPS or metadata")
    scope = registry.get("commercial_scope", {})
    for flag in [
        "customer_copy_changed",
        "durable_municipal_memory_write_performed",
        "acontext_write_performed",
        "autonomous_dispatch_enabled",
        "legal_or_approval_claim_allowed",
    ]:
        if scope.get(flag) is not False:
            raise CityOpsContractError(
                f"operator coverage summary rejects commercial scope overclaim: {flag}"
            )


def _assert_claim_boundaries(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> None:
    if not safe_to_claim:
        raise CityOpsContractError("operator coverage summary missing safe_to_claim")
    if not do_not_claim_yet:
        raise CityOpsContractError("operator coverage summary missing do_not_claim_yet")
    forbidden_safe = sorted(
        set(safe_to_claim) & set(FORBIDDEN_OPERATOR_COVERAGE_SAFE_CLAIMS)
    )
    if forbidden_safe:
        raise CityOpsContractError(
            f"operator coverage summary has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"operator coverage summary claim overlap: {overlap}")


def _assert_summary_is_conservative(summary: dict[str, Any]) -> None:
    if summary.get("schema") != PHASE1_OPERATOR_COVERAGE_SUMMARY_SCHEMA:
        raise CityOpsContractError("operator coverage summary schema mismatch")
    derived_from = summary["derived_from"]
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("operator coverage summary must stay read-only")
    for flag in [
        "writes_customer_copy",
        "writes_municipal_memory",
        "writes_live_acontext",
        "enables_dispatch_automation",
        "publishes_worker_doctrine",
    ]:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(f"operator coverage summary overclaims {flag}")
    readiness = summary["readiness"]
    promoted = [flag for flag, value in readiness.items() if value is True]
    if promoted:
        raise CityOpsContractError(
            f"operator coverage summary promoted readiness: {promoted}"
        )
    blocked = set(summary["claim_boundaries"]["do_not_claim_yet"])
    missing_blocked = [
        claim for claim in REQUIRED_OPERATOR_BLOCKED_CLAIMS if claim not in blocked
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"operator coverage summary missing blocked claims: {missing_blocked}"
        )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
