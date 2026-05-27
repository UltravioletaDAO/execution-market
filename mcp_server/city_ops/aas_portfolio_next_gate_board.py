"""Internal AAS portfolio next-gate board.

This module is the read-only continuation after the portfolio promotion ledger.
It consumes only ``aas_portfolio_promotion_ledger.json`` and turns the five AAS
family rows into a ranked internal/admin decision board for the next *separate*
gate. It deliberately does not approve any customer copy, customer delivery,
publication, public/catalog route, pricing/quote, queue launch, dispatch,
ERC-8004 reputation, live Acontext/runtime parity, exact GPS/raw metadata
release, private operator context release, or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_portfolio_promotion_ledger import (
    AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME,
    AAS_PORTFOLIO_PROMOTION_LEDGER_SAFE_CLAIM,
    AAS_PORTFOLIO_PROMOTION_LEDGER_SCHEMA,
    FAMILY_ORDER,
    LEDGER_BLOCKED_CLAIMS,
    LEDGER_FALSE_FLAGS,
    LEDGER_ID,
    LEDGER_STATUS,
    SUMMARY_COUNTERS_ZERO,
    load_aas_portfolio_promotion_ledger,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_PORTFOLIO_NEXT_GATE_BOARD_SCHEMA = "city_ops.aas_portfolio_next_gate_board.v1"
AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME = "aas_portfolio_next_gate_board.json"
AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM = "admin_aas_portfolio_next_gate_board_landed"

BOARD_ID = "execution_market.aas.portfolio_next_gate_board.2026_05_27_0100"
SCOPE = "internal_admin_next_gate_board_only_no_customer_exposure"
BOARD_STATUS = "ranked_next_gate_board_all_launch_customer_runtime_claims_blocked"
SOURCE_POLICY = "consume_only_persisted_aas_portfolio_promotion_ledger_json"

BOARD_BLOCKED_CLAIMS = [
    *LEDGER_BLOCKED_CLAIMS,
    "next_gate_board_is_human_approval",
    "next_gate_board_customer_copy_ready",
    "next_gate_board_customer_delivery_approved",
    "next_gate_board_publication_approved",
    "next_gate_board_public_or_catalog_route_ready",
    "next_gate_board_public_price_or_customer_quote_ready",
    "next_gate_board_operator_queue_launch_ready",
    "next_gate_board_autonomous_dispatch_ready",
    "next_gate_board_erc8004_reputation_ready",
    "next_gate_board_worker_skill_dna_ready",
    "next_gate_board_live_acontext_runtime_parity",
    "next_gate_board_payment_or_production_reverified",
    "next_gate_board_exact_gps_or_raw_metadata_release_allowed",
    "next_gate_board_private_operator_context_release_allowed",
    "next_gate_board_legal_regulator_emergency_safety_repair_insurance_authority",
    "next_gate_board_dataset_or_analytics_publication_ready",
    "next_gate_board_worker_copyable_doctrine_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(BOARD_BLOCKED_CLAIMS) | {
    "human_approval_ready",
    "human_operator_approval_recorded",
    "customer_copy_ready",
    "customer_delivery_ready",
    "customer_delivery_approved",
    "publishable",
    "publication_ready",
    "publication_approved",
    "public_catalog_ready",
    "public_route_ready",
    "catalog_ready",
    "controlled_pilot_ready",
    "public_price_ready",
    "pricing_ready",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "autonomous_dispatch_ready",
    "reputation_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "acontext_sink_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "private_context_release_allowed",
    "legal_or_regulator_authority_ready",
    "emergency_response",
    "safety_certification",
    "repair_diagnosis",
    "insurance_adjustment",
    "dataset_publication_ready",
    "analytics_ready",
    "statistical_representativeness_ready",
    "continuous_monitoring_ready",
    "worker_copyable_doctrine_ready",
}

BOARD_FALSE_FLAGS = [
    "board_records_human_operator_approval",
    "board_approves_selected_boundary",
    "board_authorizes_customer_copy",
    "board_authorizes_customer_delivery",
    "board_authorizes_publication",
    "board_authorizes_public_or_catalog_route",
    "board_authorizes_public_pricing_or_customer_quote",
    "board_authorizes_queue_or_dispatch",
    "board_authorizes_reputation_attachment",
    "board_proves_live_acontext_runtime_parity",
    "board_reverifies_payment_or_production_health",
    "board_allows_exact_gps_or_raw_metadata_release",
    "board_releases_private_operator_context",
    "board_creates_worker_skill_dna_or_copyable_doctrine",
    "network_route_registered",
    "public_route_registered",
    "customer_visible",
    "catalog_visible",
    "pricing_enabled",
    "worker_visible",
    "dispatch_enabled",
    "writes_live_acontext",
    "emits_reputation_receipts",
]

_GATE_SPECS = {
    "retail_reality_as_a_service": {
        "rank": 1,
        "gate_family": "human_selected_boundary_review",
        "next_gate_action": "create_separate_human_operator_approval_record_only_if_explicitly_authorized",
        "operator_choice": "best_first_human_review_candidate_because_boundary_is_already_selected_but_pending",
        "human_authorization_required": True,
        "default_without_human": "keep_pending_status_card_and_do_not_promote",
    },
    "compliance_desk_as_a_service": {
        "rank": 2,
        "gate_family": "delivery_publication_boundary_review",
        "next_gate_action": "create_delivery_publication_gate_only_if_exact_delivery_path_is_authorized",
        "operator_choice": "second_candidate_because_label_boundary_is_approved_but_delivery_path_is_absent",
        "human_authorization_required": True,
        "default_without_human": "keep_internal_label_approval_only",
    },
    "document_handoff_logistics_as_a_service": {
        "rank": 3,
        "gate_family": "internal_package_review_prerequisite",
        "next_gate_action": "keep_hold_or_create_package_review_decision_without_customer_delivery",
        "operator_choice": "internal_prerequisite_only_due_legal_identity_custody_and_filing_authority_blocks",
        "human_authorization_required": False,
        "default_without_human": "keep_explicit_hold_decision",
    },
    "incident_verification_as_a_service": {
        "rank": 4,
        "gate_family": "internal_triage_language_review_prerequisite",
        "next_gate_action": "keep_hold_or_review_triage_language_and_escalation_exclusions",
        "operator_choice": "internal_prerequisite_only_due_emergency_safety_repair_insurance_and_fault_blocks",
        "human_authorization_required": False,
        "default_without_human": "keep_explicit_hold_decision",
    },
    "local_data_collection_as_a_service": {
        "rank": 5,
        "gate_family": "method_boundary_review_prerequisite",
        "next_gate_action": "keep_hold_or_review_method_boundary_without_dataset_or_analytics_claims",
        "operator_choice": "internal_prerequisite_only_due_dataset_analytics_representativeness_and_monitoring_blocks",
        "human_authorization_required": False,
        "default_without_human": "keep_explicit_hold_decision",
    },
}

_GATE_FALSE_FLAGS = [
    "this_board_approves_gate",
    "customer_delivery_authorized",
    "publication_authorized",
    "public_or_catalog_route_ready",
    "pricing_or_customer_quote_ready",
    "queue_or_dispatch_ready",
    "reputation_attachment_ready",
    "live_acontext_runtime_parity",
    "exact_gps_or_raw_metadata_release_allowed",
    "worker_copyable_doctrine_ready",
]


def _canonical_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_aas_portfolio_next_gate_board(
    *,
    artifact_dir: Path | None = None,
    source_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin next-gate board."""

    ledger = source_ledger or load_aas_portfolio_promotion_ledger(artifact_dir=artifact_dir)
    _assert_source_ledger_conservative(ledger)

    safe_to_claim = _dedupe(
        [
            *ledger["safe_to_claim"],
            AAS_PORTFOLIO_PROMOTION_LEDGER_SAFE_CLAIM,
            AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe([*ledger["do_not_claim_yet"], *BOARD_BLOCKED_CLAIMS])
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    next_gate_rows = _next_gate_rows(ledger["family_rows"])
    board: dict[str, Any] = {
        "schema": AAS_PORTFOLIO_NEXT_GATE_BOARD_SCHEMA,
        "board_id": BOARD_ID,
        "scope": SCOPE,
        "board_status": BOARD_STATUS,
        "source_policy": SOURCE_POLICY,
        "source_ledger_file": AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME,
        "source_ledger_id": ledger["ledger_id"],
        "source_ledger_digest_sha256": _canonical_digest(ledger),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "summary": {
            "families_on_board": 5,
            "source_consumed": "aas_portfolio_promotion_ledger.json_only",
            "candidate_human_review_gates": 2,
            "internal_prerequisite_gates": 3,
            "gates_ready_without_separate_authorization": 0,
            "customer_copy_approved": False,
            "customer_delivery_approved": False,
            "publication_approved": False,
            "public_or_catalog_routes_approved": False,
            "public_prices_or_customer_quotes_approved": False,
            "queue_dispatch_reputation_runtime_gps_worker_doctrine_approved": False,
        },
        "default_decision": {
            "if_no_human_authorization": "do_not_promote_any_family_keep_portfolio_ledger_read_only",
            "if_human_review_available": "pick_exactly_one_ranked_gate_and_create_a_separate_artifact",
            "if_runtime_repair_available": "keep_Acontext_runtime_repair_isolated_from_customer_exposure",
            "this_board_is_not_the_approval_record": True,
        },
        "next_gate_rows": next_gate_rows,
        "operator_review_menu": {
            "ranked_first_choice": next_gate_rows[0]["family_id"],
            "reason": next_gate_rows[0]["operator_choice"],
            "allowed_actions": [
                "keep_all_families_internal_admin_only",
                "create_one_separate_human_operator_approval_record_for_rank_1_or_rank_2_only_if_explicitly_authorized",
                "create_one_internal_prerequisite_review_artifact_for_rank_3_to_rank_5_without_customer_exposure",
                "repair_Acontext_runtime_prerequisites_in_a_separate_lane_without_inference_to_customer_readiness",
            ],
            "forbidden_actions": [
                "approve_customer_copy_delivery_or_publication_from_this_board",
                "mount_public_or_catalog_routes_from_this_board",
                "publish_prices_or_customer_quotes_from_this_board",
                "launch_operator_queue_or_dispatch_from_this_board",
                "attach_ERC_8004_reputation_from_this_board",
                "claim_live_Acontext_runtime_parity_from_this_board",
                "release_exact_GPS_raw_metadata_or_private_operator_context_from_this_board",
                "publish_worker_copyable_AAS_doctrine_from_this_board",
            ],
        },
        **{flag: False for flag in BOARD_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this as an internal/admin next-gate menu only. If Saúl wants customer exposure, "
            "create a separate human-operator approval artifact for one exact boundary and delivery path. "
            "Otherwise keep every family internal/admin-only and do not infer routes, prices, dispatch, "
            "reputation, runtime parity, raw-location release, authority claims, or worker doctrine."
        ),
    }
    _assert_board_is_conservative(board, ledger=ledger)
    return board


def write_aas_portfolio_next_gate_board(artifact_dir: Path | None = None) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    board = build_aas_portfolio_next_gate_board(artifact_dir=target_dir)
    path = target_dir / AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME
    path.write_text(json.dumps(board, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_portfolio_next_gate_board(artifact_dir: Path | None = None) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        board = json.load(fh)
    if not isinstance(board, dict):
        raise CityOpsContractError("AAS portfolio next-gate board must be a JSON object")
    ledger = load_aas_portfolio_promotion_ledger(artifact_dir=source_dir)
    _assert_board_is_conservative(board, ledger=ledger)
    return board


def _next_gate_rows(family_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_id = {row["family_id"]: row for row in family_rows}
    for family_id, spec in sorted(_GATE_SPECS.items(), key=lambda item: item[1]["rank"]):
        source = by_id[family_id]
        row = {
            "rank": spec["rank"],
            "family_id": family_id,
            "family_label": source["family_label"],
            "current_decision_posture": source["decision_posture"],
            "current_highest_safe_boundary": source["current_highest_safe_boundary"],
            "source_recommended_next_gate": source["recommended_next_gate"],
            "latest_safe_claim": source["latest_safe_claim"],
            "gate_family": spec["gate_family"],
            "next_gate_action": spec["next_gate_action"],
            "operator_choice": spec["operator_choice"],
            "human_authorization_required": spec["human_authorization_required"],
            "default_without_human": spec["default_without_human"],
            "family_specific_blocked_claims": list(source["family_specific_blocked_claims"]),
        }
        row.update({flag: False for flag in _GATE_FALSE_FLAGS})
        rows.append(row)
    return rows


def _assert_source_ledger_conservative(ledger: dict[str, Any]) -> None:
    if ledger.get("schema") != AAS_PORTFOLIO_PROMOTION_LEDGER_SCHEMA:
        raise CityOpsContractError("AAS portfolio next-gate board source ledger schema drift")
    if ledger.get("ledger_id") != LEDGER_ID:
        raise CityOpsContractError("AAS portfolio next-gate board source ledger id drift")
    if ledger.get("ledger_status") != LEDGER_STATUS:
        raise CityOpsContractError("AAS portfolio next-gate board source ledger status drift")
    if AAS_PORTFOLIO_PROMOTION_LEDGER_SAFE_CLAIM not in ledger.get("safe_to_claim", []):
        raise CityOpsContractError("AAS portfolio next-gate board source safe claim missing")
    forbidden_safe = set(ledger.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS portfolio next-gate board source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    if set(ledger.get("safe_to_claim", [])) & set(ledger.get("do_not_claim_yet", [])):
        raise CityOpsContractError("AAS portfolio next-gate board source safe/blocked overlap")
    missing_blocked = set(LEDGER_BLOCKED_CLAIMS) - set(ledger.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS portfolio next-gate board source missing blocked claims: {sorted(missing_blocked)}"
        )
    if [row.get("family_id") for row in ledger.get("family_rows", [])] != FAMILY_ORDER:
        raise CityOpsContractError("AAS portfolio next-gate board source family row order drift")
    summary = ledger.get("ledger_summary", {})
    if summary.get("families_tracked") != 5:
        raise CityOpsContractError("AAS portfolio next-gate board source family count drift")
    if summary.get("families_with_internal_label_approval_only") != 1:
        raise CityOpsContractError("AAS portfolio next-gate board source approval-only count drift")
    if summary.get("families_held") != 3:
        raise CityOpsContractError("AAS portfolio next-gate board source held count drift")
    if summary.get("families_pending_human_review_not_approved") != 1:
        raise CityOpsContractError("AAS portfolio next-gate board source pending count drift")
    for count_key in SUMMARY_COUNTERS_ZERO:
        if summary.get(count_key) != 0:
            raise CityOpsContractError(
                f"AAS portfolio next-gate board source promoted summary {count_key}"
            )
    for flag in LEDGER_FALSE_FLAGS:
        if ledger.get(flag) is not False:
            raise CityOpsContractError(f"AAS portfolio next-gate board source promoted {flag}")
    for row in ledger.get("family_rows", []):
        for row_flag in [
            "customer_delivery_authorized",
            "publication_authorized",
            "public_or_catalog_route_ready",
            "pricing_or_customer_quote_ready",
            "queue_or_dispatch_ready",
            "reputation_attachment_ready",
            "live_acontext_runtime_parity",
            "exact_gps_or_raw_metadata_release_allowed",
            "worker_copyable_doctrine_ready",
        ]:
            if row.get(row_flag) is not False:
                raise CityOpsContractError(
                    f"AAS portfolio next-gate board source row promoted {row.get('family_id')} {row_flag}"
                )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    forbidden_safe = set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS portfolio next-gate board forbidden safe claims: {sorted(forbidden_safe)}"
        )
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"AAS portfolio next-gate board safe/blocked overlap: {sorted(overlap)}"
        )
    missing_blocked = set(BOARD_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS portfolio next-gate board missing blocked claims: {sorted(missing_blocked)}"
        )


def _assert_board_is_conservative(board: dict[str, Any], *, ledger: dict[str, Any]) -> None:
    _assert_source_ledger_conservative(ledger)
    if board.get("schema") != AAS_PORTFOLIO_NEXT_GATE_BOARD_SCHEMA:
        raise CityOpsContractError("AAS portfolio next-gate board schema drift")
    if board.get("board_id") != BOARD_ID:
        raise CityOpsContractError("AAS portfolio next-gate board id drift")
    if board.get("scope") != SCOPE:
        raise CityOpsContractError("AAS portfolio next-gate board scope drift")
    if board.get("board_status") != BOARD_STATUS:
        raise CityOpsContractError("AAS portfolio next-gate board status drift")
    if board.get("source_policy") != SOURCE_POLICY:
        raise CityOpsContractError("AAS portfolio next-gate board source policy drift")
    if board.get("source_ledger_digest_sha256") != _canonical_digest(ledger):
        raise CityOpsContractError("AAS portfolio next-gate board source digest drift")
    if AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM not in board.get("safe_to_claim", []):
        raise CityOpsContractError("AAS portfolio next-gate board safe claim missing")
    _assert_claim_boundaries(board.get("safe_to_claim", []), board.get("do_not_claim_yet", []))
    if board.get("still_blocked_claims") != board.get("do_not_claim_yet"):
        raise CityOpsContractError("AAS portfolio next-gate board blocked claims drift")
    summary = board.get("summary", {})
    expected_summary = {
        "families_on_board": 5,
        "candidate_human_review_gates": 2,
        "internal_prerequisite_gates": 3,
        "gates_ready_without_separate_authorization": 0,
        "customer_copy_approved": False,
        "customer_delivery_approved": False,
        "publication_approved": False,
        "public_or_catalog_routes_approved": False,
        "public_prices_or_customer_quotes_approved": False,
        "queue_dispatch_reputation_runtime_gps_worker_doctrine_approved": False,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise CityOpsContractError(f"AAS portfolio next-gate board summary drift {key}")
    rows = board.get("next_gate_rows", [])
    if [row.get("family_id") for row in rows] != [
        "retail_reality_as_a_service",
        "compliance_desk_as_a_service",
        "document_handoff_logistics_as_a_service",
        "incident_verification_as_a_service",
        "local_data_collection_as_a_service",
    ]:
        raise CityOpsContractError("AAS portfolio next-gate board row order drift")
    if [row.get("rank") for row in rows] != [1, 2, 3, 4, 5]:
        raise CityOpsContractError("AAS portfolio next-gate board rank drift")
    if [row.get("latest_safe_claim") for row in rows] != [
        _source_row(ledger, row["family_id"])["latest_safe_claim"] for row in rows
    ]:
        raise CityOpsContractError("AAS portfolio next-gate board source safe claim drift")
    for row in rows:
        spec = _GATE_SPECS[row["family_id"]]
        if row.get("gate_family") != spec["gate_family"]:
            raise CityOpsContractError("AAS portfolio next-gate board gate family drift")
        if row.get("human_authorization_required") != spec["human_authorization_required"]:
            raise CityOpsContractError("AAS portfolio next-gate board human authorization drift")
        for flag in _GATE_FALSE_FLAGS:
            if row.get(flag) is not False:
                raise CityOpsContractError(
                    f"AAS portfolio next-gate board row promoted {row.get('family_id')} {flag}"
                )
    for flag in BOARD_FALSE_FLAGS:
        if board.get(flag) is not False:
            raise CityOpsContractError(f"AAS portfolio next-gate board promoted {flag}")
    if board.get("default_decision", {}).get("this_board_is_not_the_approval_record") is not True:
        raise CityOpsContractError("AAS portfolio next-gate board approval-record boundary drift")
    menu = board.get("operator_review_menu", {})
    if menu.get("ranked_first_choice") != "retail_reality_as_a_service":
        raise CityOpsContractError("AAS portfolio next-gate board first choice drift")
    forbidden_actions = set(menu.get("forbidden_actions", []))
    required_forbidden = {
        "approve_customer_copy_delivery_or_publication_from_this_board",
        "mount_public_or_catalog_routes_from_this_board",
        "publish_prices_or_customer_quotes_from_this_board",
        "launch_operator_queue_or_dispatch_from_this_board",
        "attach_ERC_8004_reputation_from_this_board",
        "claim_live_Acontext_runtime_parity_from_this_board",
        "release_exact_GPS_raw_metadata_or_private_operator_context_from_this_board",
        "publish_worker_copyable_AAS_doctrine_from_this_board",
    }
    if not required_forbidden <= forbidden_actions:
        raise CityOpsContractError("AAS portfolio next-gate board forbidden action drift")


def _source_row(ledger: dict[str, Any], family_id: str) -> dict[str, Any]:
    for row in ledger.get("family_rows", []):
        if row.get("family_id") == family_id:
            return row
    raise CityOpsContractError(f"AAS portfolio next-gate board source row missing {family_id}")
