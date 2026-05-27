"""Internal AAS portfolio operator-authorization packet.

This module is the no-human-answer continuation after the AAS portfolio
next-gate board. It converts the ranked board into a narrow internal/admin
packet that names the two gates that would require an explicit human operator
choice later. The packet itself records no approval, no selected authorization,
no customer copy or delivery, no publication, no public/catalog route, no
pricing/quote, no queue/dispatch, no reputation, no live Acontext/runtime
parity, no exact GPS/raw metadata/private-context release, no legal/regulator
or domain-authority claim, and no worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_portfolio_next_gate_board import (
    AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME,
    AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM,
    AAS_PORTFOLIO_NEXT_GATE_BOARD_SCHEMA,
    BOARD_BLOCKED_CLAIMS,
    BOARD_FALSE_FLAGS,
    BOARD_ID,
    BOARD_STATUS,
    SOURCE_POLICY as NEXT_GATE_SOURCE_POLICY,
    load_aas_portfolio_next_gate_board,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_SCHEMA = (
    "city_ops.aas_portfolio_operator_authorization_packet.v1"
)
AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_FILENAME = (
    "aas_portfolio_operator_authorization_packet.json"
)
AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_SAFE_CLAIM = (
    "admin_aas_portfolio_operator_authorization_packet_landed"
)

PACKET_ID = "execution_market.aas.portfolio_operator_authorization_packet.2026_05_27_0200"
SCOPE = "internal_admin_operator_authorization_packet_only_no_customer_exposure"
PACKET_STATUS = "questions_prepared_no_operator_answer_recorded_all_launch_claims_blocked"
SOURCE_POLICY = "consume_only_persisted_aas_portfolio_next_gate_board_json"
DEFAULT_IF_UNANSWERED = "keep_all_families_internal_admin_only_no_promotion"

PACKET_BLOCKED_CLAIMS = [
    *BOARD_BLOCKED_CLAIMS,
    "operator_authorization_packet_is_human_approval",
    "operator_authorization_packet_records_operator_answer",
    "operator_authorization_packet_selects_candidate_for_approval",
    "operator_authorization_packet_authorizes_customer_copy",
    "operator_authorization_packet_authorizes_customer_delivery",
    "operator_authorization_packet_authorizes_publication",
    "operator_authorization_packet_authorizes_public_or_catalog_route",
    "operator_authorization_packet_authorizes_public_pricing_or_customer_quote",
    "operator_authorization_packet_authorizes_operator_queue_launch",
    "operator_authorization_packet_authorizes_autonomous_dispatch",
    "operator_authorization_packet_authorizes_erc8004_reputation",
    "operator_authorization_packet_authorizes_worker_skill_dna",
    "operator_authorization_packet_authorizes_live_acontext_runtime_parity",
    "operator_authorization_packet_authorizes_payment_or_production_reverification",
    "operator_authorization_packet_authorizes_exact_gps_or_raw_metadata_release",
    "operator_authorization_packet_authorizes_private_operator_context_release",
    "operator_authorization_packet_authorizes_domain_legal_regulator_emergency_safety_repair_insurance_or_dataset_claims",
    "operator_authorization_packet_authorizes_worker_copyable_doctrine",
]

FORBIDDEN_SAFE_CLAIMS = set(PACKET_BLOCKED_CLAIMS) | {
    "human_approval_ready",
    "human_operator_approval_recorded",
    "operator_answer_recorded",
    "selected_for_approval",
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
    "payment_production_reverified",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "exact_gps_or_raw_metadata_exposure_allowed",
    "private_context_release_allowed",
    "domain_authority_ready",
    "legal_or_regulator_authority_ready",
    "emergency_response",
    "safety_certification",
    "repair_diagnosis",
    "insurance_adjustment",
    "dataset_publication_ready",
    "analytics_ready",
    "worker_copyable_doctrine_ready",
}

PACKET_FALSE_FLAGS = [
    *BOARD_FALSE_FLAGS,
    "packet_records_human_operator_approval",
    "packet_records_operator_answer",
    "packet_selects_candidate_for_approval",
    "packet_authorizes_customer_copy",
    "packet_authorizes_customer_delivery",
    "packet_authorizes_publication",
    "packet_authorizes_public_or_catalog_route",
    "packet_authorizes_public_pricing_or_customer_quote",
    "packet_authorizes_queue_or_dispatch",
    "packet_authorizes_reputation_attachment",
    "packet_proves_live_acontext_runtime_parity",
    "packet_reverifies_payment_or_production_health",
    "packet_allows_exact_gps_or_raw_metadata_release",
    "packet_releases_private_operator_context",
    "packet_creates_worker_skill_dna_or_copyable_doctrine",
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

_CANDIDATE_SPECS = {
    "retail_reality_as_a_service": {
        "authorization_question": (
            "Should a future separate human-operator approval record be created for "
            "the already selected Retail Reality boundary?"
        ),
        "required_explicit_inputs": [
            "operator_name_or_review_identity",
            "exact_selected_boundary_digest_from_retail_reality_request",
            "approved_or_hold_decision_for_that_exact_boundary",
            "redaction_checks_reconfirmed",
            "delivery_path_decision_explicitly_none_or_named_in_separate_record",
            "still_blocked_claims_confirmed",
        ],
        "answer_artifact_if_authorized": "retail_reality_human_operator_approval_record_or_hold_record",
        "default_without_answer": "keep_pending_status_card_not_approved",
    },
    "compliance_desk_as_a_service": {
        "authorization_question": (
            "Should a future delivery/publication gate be opened for Compliance Desk, "
            "and if so what exact delivery path is authorized?"
        ),
        "required_explicit_inputs": [
            "operator_name_or_review_identity",
            "exact_delivery_path_or_none",
            "approved_text_boundary_digest_from_existing_approval_record",
            "redaction_checks_reconfirmed_at_delivery_time",
            "domain_authority_exclusions_reconfirmed",
            "publication_and_customer_delivery_decision_kept_separate",
            "still_blocked_claims_confirmed",
        ],
        "answer_artifact_if_authorized": "aas_single_boundary_delivery_publication_gate_or_hold_record",
        "default_without_answer": "keep_internal_label_approval_only_no_delivery_path",
    },
}

_CANDIDATE_FALSE_FLAGS = [
    "operator_answer_recorded",
    "selected_for_approval",
    "human_operator_approval_recorded",
    "customer_copy_authorized",
    "customer_delivery_authorized",
    "publication_authorized",
    "public_or_catalog_route_ready",
    "pricing_or_customer_quote_ready",
    "queue_or_dispatch_ready",
    "reputation_attachment_ready",
    "live_acontext_runtime_parity",
    "exact_gps_or_raw_metadata_release_allowed",
    "private_operator_context_release_allowed",
    "domain_legal_regulator_emergency_safety_repair_insurance_or_dataset_claims_allowed",
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


def build_aas_portfolio_operator_authorization_packet(
    *,
    artifact_dir: Path | None = None,
    source_board: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin operator-authorization packet."""

    board = source_board or load_aas_portfolio_next_gate_board(artifact_dir=artifact_dir)
    _assert_source_board_conservative(board)

    safe_to_claim = _dedupe(
        [
            *board["safe_to_claim"],
            AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM,
            AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe([*board["do_not_claim_yet"], *PACKET_BLOCKED_CLAIMS])
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    candidate_rows = _candidate_rows(board["next_gate_rows"])
    packet: dict[str, Any] = {
        "schema": AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_SCHEMA,
        "packet_id": PACKET_ID,
        "scope": SCOPE,
        "packet_status": PACKET_STATUS,
        "source_policy": SOURCE_POLICY,
        "source_board_file": AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME,
        "source_board_id": board["board_id"],
        "source_board_digest_sha256": _canonical_digest(board),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "summary": {
            "candidate_questions_prepared": 2,
            "operator_answers_recorded": 0,
            "candidates_selected_for_approval": 0,
            "human_approval_records_created": 0,
            "delivery_paths_authorized": 0,
            "families_kept_internal_admin_only_by_default": 5,
            "customer_copy_delivery_publication_route_pricing_dispatch_reputation_runtime_gps_worker_doctrine_approved": False,
        },
        "default_if_unanswered": DEFAULT_IF_UNANSWERED,
        "candidate_rows": candidate_rows,
        "operator_decision_form": {
            "form_status": "blank_no_operator_answer_recorded",
            "allowed_future_answers": [
                "leave_all_candidates_internal_admin_only",
                "authorize_exactly_one_retail_reality_approval_record_in_separate_artifact",
                "authorize_exactly_one_compliance_delivery_path_gate_in_separate_artifact",
            ],
            "forbidden_answers_in_this_packet": [
                "approve_customer_copy_delivery_or_publication_here",
                "select_more_than_one_candidate_here",
                "mount_public_or_catalog_routes_here",
                "publish_prices_or_customer_quotes_here",
                "launch_operator_queue_or_dispatch_here",
                "attach_ERC_8004_reputation_here",
                "claim_live_Acontext_runtime_parity_here",
                "release_exact_GPS_raw_metadata_or_private_operator_context_here",
                "publish_worker_copyable_AAS_doctrine_here",
            ],
            "chosen_answer": None,
            "operator_answer_recorded": False,
            "this_form_is_not_an_approval_record": True,
        },
        **{flag: False for flag in PACKET_FALSE_FLAGS},
        "still_blocked_claims": do_not_claim_yet,
        "operator_instruction": (
            "Use this packet as the morning decision prompt only. If Saúl chooses customer "
            "exposure, create exactly one separate answer artifact with the exact boundary, "
            "redactions, delivery-path decision, and still-blocked claims. Until then, keep all "
            "five AAS families internal/admin-only and do not infer delivery, publication, routes, "
            "pricing, dispatch, reputation, runtime parity, raw-location release, authority claims, "
            "or worker doctrine."
        ),
    }
    _assert_packet_is_conservative(packet, board=board)
    return packet


def write_aas_portfolio_operator_authorization_packet(artifact_dir: Path | None = None) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    packet = build_aas_portfolio_operator_authorization_packet(artifact_dir=target_dir)
    path = target_dir / AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_portfolio_operator_authorization_packet(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        packet = json.load(fh)
    if not isinstance(packet, dict):
        raise CityOpsContractError("AAS portfolio operator authorization packet must be a JSON object")
    board = load_aas_portfolio_next_gate_board(artifact_dir=source_dir)
    _assert_packet_is_conservative(packet, board=board)
    return packet


def _candidate_rows(next_gate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {row["family_id"]: row for row in next_gate_rows}
    rows: list[dict[str, Any]] = []
    for family_id in ["retail_reality_as_a_service", "compliance_desk_as_a_service"]:
        source = by_id[family_id]
        spec = _CANDIDATE_SPECS[family_id]
        row = {
            "candidate_rank": source["rank"],
            "family_id": family_id,
            "family_label": source["family_label"],
            "gate_family": source["gate_family"],
            "source_next_gate_action": source["next_gate_action"],
            "source_current_highest_safe_boundary": source["current_highest_safe_boundary"],
            "source_latest_safe_claim": source["latest_safe_claim"],
            "authorization_question": spec["authorization_question"],
            "required_explicit_inputs": list(spec["required_explicit_inputs"]),
            "answer_artifact_if_authorized": spec["answer_artifact_if_authorized"],
            "default_without_answer": spec["default_without_answer"],
            "candidate_text_values_included": False,
            "authorized_delivery_path": "none_until_separate_operator_answer_artifact",
            "family_specific_blocked_claims": list(source["family_specific_blocked_claims"]),
        }
        row.update({flag: False for flag in _CANDIDATE_FALSE_FLAGS})
        rows.append(row)
    return rows


def _assert_source_board_conservative(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_PORTFOLIO_NEXT_GATE_BOARD_SCHEMA:
        raise CityOpsContractError("AAS portfolio operator authorization packet source board schema drift")
    if board.get("board_id") != BOARD_ID:
        raise CityOpsContractError("AAS portfolio operator authorization packet source board id drift")
    if board.get("board_status") != BOARD_STATUS:
        raise CityOpsContractError("AAS portfolio operator authorization packet source board status drift")
    if board.get("source_policy") != NEXT_GATE_SOURCE_POLICY:
        raise CityOpsContractError("AAS portfolio operator authorization packet source board policy drift")
    if AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM not in board.get("safe_to_claim", []):
        raise CityOpsContractError("AAS portfolio operator authorization packet source safe claim missing")
    forbidden_safe = set(board.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS portfolio operator authorization packet source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(BOARD_BLOCKED_CLAIMS) - set(board.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS portfolio operator authorization packet source missing blocked claims: {sorted(missing_blocked)}"
        )
    summary = board.get("summary", {})
    for key in [
        "gates_ready_without_separate_authorization",
        "customer_copy_approved",
        "customer_delivery_approved",
        "publication_approved",
        "public_or_catalog_routes_approved",
        "public_prices_or_customer_quotes_approved",
        "queue_dispatch_reputation_runtime_gps_worker_doctrine_approved",
    ]:
        expected = 0 if key == "gates_ready_without_separate_authorization" else False
        if summary.get(key) != expected:
            raise CityOpsContractError(
                f"AAS portfolio operator authorization packet source promoted summary {key}"
            )
    for flag in BOARD_FALSE_FLAGS:
        if board.get(flag) is not False:
            raise CityOpsContractError(
                f"AAS portfolio operator authorization packet source promoted {flag}"
            )
    rows = board.get("next_gate_rows", [])
    if [row.get("family_id") for row in rows[:2]] != [
        "retail_reality_as_a_service",
        "compliance_desk_as_a_service",
    ]:
        raise CityOpsContractError("AAS portfolio operator authorization packet source candidate order drift")
    for row in rows:
        for flag in [
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
        ]:
            if row.get(flag) is not False:
                raise CityOpsContractError(
                    f"AAS portfolio operator authorization packet source row promoted {row.get('family_id')} {flag}"
                )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    forbidden_safe = set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS portfolio operator authorization packet forbidden safe claims: {sorted(forbidden_safe)}"
        )
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"AAS portfolio operator authorization packet safe/blocked overlap: {sorted(overlap)}"
        )
    missing_blocked = set(PACKET_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS portfolio operator authorization packet missing blocked claims: {sorted(missing_blocked)}"
        )


def _assert_packet_is_conservative(packet: dict[str, Any], *, board: dict[str, Any]) -> None:
    _assert_source_board_conservative(board)
    if packet.get("schema") != AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_SCHEMA:
        raise CityOpsContractError("AAS portfolio operator authorization packet schema drift")
    if packet.get("packet_id") != PACKET_ID:
        raise CityOpsContractError("AAS portfolio operator authorization packet id drift")
    if packet.get("scope") != SCOPE:
        raise CityOpsContractError("AAS portfolio operator authorization packet scope drift")
    if packet.get("packet_status") != PACKET_STATUS:
        raise CityOpsContractError("AAS portfolio operator authorization packet status drift")
    if packet.get("source_policy") != SOURCE_POLICY:
        raise CityOpsContractError("AAS portfolio operator authorization packet source policy drift")
    if packet.get("source_board_digest_sha256") != _canonical_digest(board):
        raise CityOpsContractError("AAS portfolio operator authorization packet source digest drift")
    if AAS_PORTFOLIO_OPERATOR_AUTHORIZATION_PACKET_SAFE_CLAIM not in packet.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("AAS portfolio operator authorization packet safe claim missing")
    _assert_claim_boundaries(packet.get("safe_to_claim", []), packet.get("do_not_claim_yet", []))
    if packet.get("still_blocked_claims") != packet.get("do_not_claim_yet"):
        raise CityOpsContractError("AAS portfolio operator authorization packet blocked claims drift")
    summary = packet.get("summary", {})
    expected_summary = {
        "candidate_questions_prepared": 2,
        "operator_answers_recorded": 0,
        "candidates_selected_for_approval": 0,
        "human_approval_records_created": 0,
        "delivery_paths_authorized": 0,
        "families_kept_internal_admin_only_by_default": 5,
        "customer_copy_delivery_publication_route_pricing_dispatch_reputation_runtime_gps_worker_doctrine_approved": False,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise CityOpsContractError(
                f"AAS portfolio operator authorization packet summary drift {key}"
            )
    rows = packet.get("candidate_rows", [])
    if [row.get("family_id") for row in rows] != [
        "retail_reality_as_a_service",
        "compliance_desk_as_a_service",
    ]:
        raise CityOpsContractError("AAS portfolio operator authorization packet candidate row order drift")
    if [row.get("candidate_rank") for row in rows] != [1, 2]:
        raise CityOpsContractError("AAS portfolio operator authorization packet candidate rank drift")
    for row in rows:
        if row.get("candidate_text_values_included") is not False:
            raise CityOpsContractError("AAS portfolio operator authorization packet exposed candidate text")
        if row.get("authorized_delivery_path") != "none_until_separate_operator_answer_artifact":
            raise CityOpsContractError("AAS portfolio operator authorization packet delivery path drift")
        if row.get("source_latest_safe_claim") != _source_row(board, row["family_id"])["latest_safe_claim"]:
            raise CityOpsContractError("AAS portfolio operator authorization packet source safe claim drift")
        for flag in _CANDIDATE_FALSE_FLAGS:
            if row.get(flag) is not False:
                raise CityOpsContractError(
                    f"AAS portfolio operator authorization packet candidate promoted {row.get('family_id')} {flag}"
                )
    form = packet.get("operator_decision_form", {})
    if form.get("operator_answer_recorded") is not False:
        raise CityOpsContractError("AAS portfolio operator authorization packet recorded answer")
    if form.get("chosen_answer") is not None:
        raise CityOpsContractError("AAS portfolio operator authorization packet selected answer")
    if form.get("this_form_is_not_an_approval_record") is not True:
        raise CityOpsContractError("AAS portfolio operator authorization packet approval boundary drift")
    for flag in PACKET_FALSE_FLAGS:
        if packet.get(flag) is not False:
            raise CityOpsContractError(
                f"AAS portfolio operator authorization packet promoted {flag}"
            )


def _source_row(board: dict[str, Any], family_id: str) -> dict[str, Any]:
    for row in board.get("next_gate_rows", []):
        if row.get("family_id") == family_id:
            return row
    raise CityOpsContractError(
        f"AAS portfolio operator authorization packet source row missing {family_id}"
    )
