"""Controlled pilot readiness board for Phase 1 City Counter Ops packages.

This module summarizes the current Phase 1 CaaS packaging posture without
promoting customer copy, public catalog, route wrappers, live Acontext,
autonomous dispatch, ERC-8004 reputation, worker Skill DNA, exact GPS/raw
metadata exposure, legal/regulator readiness, or worker-copyable municipal
doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_packet_submission_internal_package_record import (
    PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    load_phase1_packet_submission_internal_package_record,
)
from .phase1_review_output_schemas import OFFER_SPEC_DIR
from .phase1_reviewed_fixtures import (
    PHASE1_REVIEWED_FIXTURE_REGISTRY_SAFE_CLAIM,
    load_phase1_reviewed_fixture_registry_summary,
)

PHASE1_CONTROLLED_PILOT_READINESS_BOARD_SCHEMA = (
    "city_ops.phase1_controlled_pilot_readiness_board.v1"
)
PHASE1_CONTROLLED_PILOT_READINESS_BOARD_FILENAME = (
    "phase1_controlled_pilot_readiness_board.json"
)
PHASE1_CONTROLLED_PILOT_READINESS_BOARD_SAFE_CLAIM = (
    "phase1_controlled_pilot_readiness_board_landed"
)

REQUIRED_OFFER_ORDER = [
    "counter_reality_check",
    "packet_submission_attempt",
    "posting_compliance_check",
]

REQUIRED_BLOCKED_CLAIMS = [
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "controlled_concierge_pilot_ready",
    "customer_pilot_exposure_ready",
    "front_door_sku_ready",
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
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS)

READINESS_FALSE_FLAGS = [
    "customer_copy_ready",
    "customer_visible_catalog_ready",
    "public_service_catalog_ready",
    "customer_pilot_exposure_allowed",
    "front_door_sku_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "worker_copyable_doctrine_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
]


def build_phase1_controlled_pilot_readiness_board(
    *,
    fixture_dir: str | Path | None = None,
    registry: dict[str, Any] | None = None,
    packet_package_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative board for Phase 1 controlled-pilot readiness.

    The board is intentionally a stoplight, not a launch authorization. It shows
    that reviewed fixture coverage exists for all three offers and that only the
    Packet Submission Attempt currently has an internal package record. It still
    blocks customer/pilot exposure until separate customer-output, live transport,
    runtime, dispatch, reputation, privacy, and worker-doctrine gates pass.
    """

    source_registry = registry or load_phase1_reviewed_fixture_registry_summary(
        fixture_dir=fixture_dir
    )
    source_packet_record = (
        packet_package_record
        or load_phase1_packet_submission_internal_package_record(fixture_dir=fixture_dir)
    )
    _assert_source_registry(source_registry)
    _assert_source_packet_record(source_packet_record)

    coverage = source_registry["coverage_by_offer"]
    offers: list[dict[str, Any]] = []
    for offer_id in REQUIRED_OFFER_ORDER:
        row = coverage[offer_id]
        has_internal_package_record = offer_id == "packet_submission_attempt"
        offers.append(
            {
                "offer": offer_id,
                "reviewed_fixture_id": row["fixture_id"],
                "proof_status_label": row["proof_status_label"],
                "outcome_status": row["outcome_status"],
                "follow_on_task_trigger": row["follow_on_task_trigger"],
                "reviewed_fixture_exists": True,
                "internal_package_record_exists": has_internal_package_record,
                "customer_output_schema_reviewed": False,
                "customer_pilot_exposure_allowed": False,
                "pilot_readiness_status": _pilot_status_for_offer(
                    offer_id, has_internal_package_record
                ),
                "blocking_gates": _blocking_gates_for_offer(
                    offer_id, has_internal_package_record
                ),
                "next_smallest_step": _next_step_for_offer(
                    offer_id, has_internal_package_record
                ),
            }
        )

    safe_to_claim = _dedupe(
        [
            PHASE1_CONTROLLED_PILOT_READINESS_BOARD_SAFE_CLAIM,
            PHASE1_REVIEWED_FIXTURE_REGISTRY_SAFE_CLAIM,
            PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *REQUIRED_BLOCKED_CLAIMS,
            *source_registry.get("do_not_claim_yet", []),
            *source_packet_record.get("do_not_claim_yet", []),
        ]
    )

    board = {
        "schema": PHASE1_CONTROLLED_PILOT_READINESS_BOARD_SCHEMA,
        "board_id": "city_counter_ops.phase1_controlled_pilot_readiness.2026_05_10",
        "scope": "internal_operator_packaging_gate_only",
        "source_registry_id": source_registry["registry_id"],
        "source_packet_package_id": source_packet_record["package_id"],
        "offer_order": REQUIRED_OFFER_ORDER,
        "offers": offers,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "global_readiness": {
            "all_phase1_offers_have_reviewed_fixture": True,
            "all_phase1_offers_have_internal_package_record": False,
            "customer_copy_ready": False,
            "customer_visible_catalog_ready": False,
            "public_service_catalog_ready": False,
            "customer_pilot_exposure_allowed": False,
            "front_door_sku_ready": False,
            "live_acontext_ready": False,
            "runtime_parity_proven": False,
            "autonomous_dispatch_ready": False,
            "reputation_ready": False,
            "worker_copyable_doctrine_ready": False,
            "exact_gps_or_raw_metadata_exposure_allowed": False,
        },
        "operator_instruction": (
            "Use this board to decide what to build next. It is not customer copy, "
            "not a public catalog, and not approval to expose a pilot SKU."
        ),
        "next_smallest_proof": (
            "Create internal package records for Counter Reality Check and Posting "
            "Compliance Check, then add a separate customer-output schema review gate "
            "before any controlled concierge pilot wording."
        ),
    }
    _assert_board_is_conservative(board)
    return board


def write_phase1_controlled_pilot_readiness_board(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the controlled-pilot readiness board beside reviewed outputs."""

    board = build_phase1_controlled_pilot_readiness_board(fixture_dir=fixture_dir)
    return _write_board(board, fixture_dir=fixture_dir)


def load_phase1_controlled_pilot_readiness_board(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted controlled-pilot readiness board."""

    path = _board_dir(fixture_dir) / PHASE1_CONTROLLED_PILOT_READINESS_BOARD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        board = json.load(fh)
    if not isinstance(board, dict):
        raise CityOpsContractError("controlled pilot readiness board must be a JSON object")
    _assert_board_is_conservative(board)
    return board


def _write_board(
    board: dict[str, Any], *, fixture_dir: str | Path | None = None
) -> Path:
    _assert_board_is_conservative(board)
    base_dir = _board_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_CONTROLLED_PILOT_READINESS_BOARD_FILENAME
    path.write_text(json.dumps(board, indent=2) + "\n", encoding="utf-8")
    return path


def _board_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _pilot_status_for_offer(offer_id: str, has_internal_package_record: bool) -> str:
    if has_internal_package_record:
        return "internal_package_recorded_not_customer_ready"
    if offer_id == "counter_reality_check":
        return "reviewed_fixture_exists_needs_internal_package_record"
    if offer_id == "posting_compliance_check":
        return "reviewed_fixture_exists_needs_internal_package_record"
    return "not_customer_ready"


def _blocking_gates_for_offer(
    offer_id: str, has_internal_package_record: bool
) -> list[str]:
    gates = [
        "customer_output_schema_review",
        "blocked_claim_adjacency_preservation",
        "operator_review_required_before_closure",
        "live_acontext_write_retrieve_parity",
        "runtime_parity_artifact",
        "dispatch_operational_evidence",
        "erc8004_reputation_proof_path",
        "worker_copyability_review",
        "gps_and_raw_metadata_privacy_review",
    ]
    if not has_internal_package_record:
        gates.insert(0, f"{offer_id}_internal_package_record")
    return gates


def _next_step_for_offer(offer_id: str, has_internal_package_record: bool) -> str:
    if has_internal_package_record:
        return (
            "Keep Packet Submission Attempt internal; add customer-output schema review "
            "only after the same package-record gate exists for the other Phase 1 offers."
        )
    if offer_id == "counter_reality_check":
        return (
            "Create a conservative Counter Reality Check internal package record from its "
            "reviewed fixture; keep customer/pilot/public readiness false."
        )
    if offer_id == "posting_compliance_check":
        return (
            "Create a conservative Posting Compliance Check internal package record from "
            "its reviewed fixture; preserve exact-GPS/raw-metadata blocks."
        )
    return "Keep offer internal until a reviewed fixture and package record exist."


def _assert_source_registry(registry: dict[str, Any]) -> None:
    if registry.get("schema") != "city_ops.phase1_reviewed_fixture_registry.v1":
        raise CityOpsContractError("controlled pilot board source registry schema mismatch")
    coverage = registry.get("coverage_by_offer")
    if not isinstance(coverage, dict):
        raise CityOpsContractError("controlled pilot board source registry missing coverage")
    missing = [offer_id for offer_id in REQUIRED_OFFER_ORDER if offer_id not in coverage]
    if missing:
        raise CityOpsContractError(f"controlled pilot board missing source offers: {missing}")
    if registry.get("operator_observability", {}).get("exact_gps_or_metadata_exposed") is not False:
        raise CityOpsContractError("controlled pilot board cannot source GPS/metadata exposure")


def _assert_source_packet_record(record: dict[str, Any]) -> None:
    if record.get("schema") != "city_ops.phase1_packet_submission_internal_package_record.v1":
        raise CityOpsContractError("controlled pilot board packet package schema mismatch")
    if record.get("offer") != "packet_submission_attempt":
        raise CityOpsContractError("controlled pilot board packet package offer drift")
    if record.get("operator_review_required_before_closure") is not True:
        raise CityOpsContractError("controlled pilot board requires operator review source")
    if record.get("forbidden_claims_preserved") is not True:
        raise CityOpsContractError("controlled pilot board requires preserved forbidden claims")
    for flag in [
        "customer_output_schema_reviewed",
        "live_acontext_ready",
        "runtime_parity_proven",
        "autonomous_dispatch_ready",
        "reputation_ready",
        "worker_copyable_doctrine_ready",
        "exact_gps_or_raw_metadata_exposure_allowed",
    ]:
        if record.get(flag) is not False:
            raise CityOpsContractError(
                f"controlled pilot board packet package readiness drift: {flag}"
            )


def _assert_board_is_conservative(board: dict[str, Any]) -> None:
    if board.get("schema") != PHASE1_CONTROLLED_PILOT_READINESS_BOARD_SCHEMA:
        raise CityOpsContractError("controlled pilot readiness board schema mismatch")
    if board.get("scope") != "internal_operator_packaging_gate_only":
        raise CityOpsContractError("controlled pilot readiness board scope drift")
    if board.get("offer_order") != REQUIRED_OFFER_ORDER:
        raise CityOpsContractError("controlled pilot readiness board offer order drift")

    offers = board.get("offers")
    if not isinstance(offers, list) or len(offers) != len(REQUIRED_OFFER_ORDER):
        raise CityOpsContractError("controlled pilot readiness board offer count mismatch")
    for expected_offer, row in zip(REQUIRED_OFFER_ORDER, offers):
        if row.get("offer") != expected_offer:
            raise CityOpsContractError("controlled pilot readiness board offer row drift")
        if row.get("reviewed_fixture_exists") is not True:
            raise CityOpsContractError("controlled pilot readiness board requires reviewed fixtures")
        if row.get("customer_output_schema_reviewed") is not False:
            raise CityOpsContractError("controlled pilot readiness board overclaims schema review")
        if row.get("customer_pilot_exposure_allowed") is not False:
            raise CityOpsContractError("controlled pilot readiness board overclaims pilot exposure")
        if not row.get("blocking_gates"):
            raise CityOpsContractError("controlled pilot readiness board missing blocking gates")

    global_readiness = board.get("global_readiness", {})
    if global_readiness.get("all_phase1_offers_have_reviewed_fixture") is not True:
        raise CityOpsContractError("controlled pilot readiness board lost fixture coverage")
    if global_readiness.get("all_phase1_offers_have_internal_package_record") is not False:
        raise CityOpsContractError("controlled pilot readiness board package coverage overclaim")
    promoted = [flag for flag in READINESS_FALSE_FLAGS if global_readiness.get(flag) is True]
    if promoted:
        raise CityOpsContractError(
            f"controlled pilot readiness board promoted readiness: {promoted}"
        )
    missing_false = [
        flag for flag in READINESS_FALSE_FLAGS if global_readiness.get(flag) is not False
    ]
    if missing_false:
        raise CityOpsContractError(
            f"controlled pilot readiness board readiness flags must be false: {missing_false}"
        )

    safe_to_claim = list(board.get("safe_to_claim", []))
    do_not_claim_yet = list(board.get("do_not_claim_yet", []))
    if not safe_to_claim or not do_not_claim_yet:
        raise CityOpsContractError("controlled pilot readiness board missing claims")
    forbidden_safe = sorted(set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS)
    if forbidden_safe:
        raise CityOpsContractError(
            f"controlled pilot readiness board has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"controlled pilot readiness board claim overlap: {overlap}")
    missing_blocked = [
        claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in do_not_claim_yet
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"controlled pilot readiness board missing blocked claims: {missing_blocked}"
        )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
