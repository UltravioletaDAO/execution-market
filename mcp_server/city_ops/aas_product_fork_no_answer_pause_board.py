"""AAS product-fork no-answer pause board.

This module is a read-only internal/admin continuation for Execution Market
AAS / City-as-a-Service when no real human/operator answer exists.  It consumes
only the portfolio next-gate board plus the Retail Reality product-exposure hold
regression guard and records the fail-closed product posture:

* no product family is approved;
* Retail Reality remains the closest review candidate, but still held;
* no customer/public exposure, pricing, queue, dispatch, reputation, runtime
  mutation, payment/production proof, raw-location release, authority claim, or
  worker-copyable doctrine is authorized; and
* stopped-project integrations remain blocked.
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
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError
from .retail_reality_product_exposure_hold_regression_guard import (
    GUARD_BLOCKED_CLAIMS,
    GUARD_FALSE_FLAGS,
    GUARD_ID,
    GUARD_STATUS,
    RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME,
    RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM,
    RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SCHEMA,
    load_retail_reality_product_exposure_hold_regression_guard,
)

AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SCHEMA = (
    "city_ops.aas_product_fork_no_answer_pause_board.v1"
)
AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME = (
    "aas_product_fork_no_answer_pause_board.json"
)
AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SAFE_CLAIM = (
    "admin_aas_product_fork_no_answer_pause_board_landed"
)

PAUSE_BOARD_ID = "execution_market.aas.product_fork_no_answer_pause_board.2026_06_02_0200"
SCOPE = "internal_admin_no_human_answer_product_fork_pause_only"
PAUSE_BOARD_STATUS = "no_answer_pause_all_product_forks_held_no_customer_exposure"
SOURCE_POLICY = "consume_only_portfolio_next_gate_board_and_retail_hold_guard_json"
DEFAULT_DECISION = "hold_all_product_forks_internal_admin_only"
RUNTIME_DECISION = "hold_no_runtime_mutation"
NEXT_ALLOWED_MOVE = (
    "wait_for_explicit_human_operator_answer_or_continue_read_only_internal_admin_review_only"
)

PAUSE_FALSE_FLAGS = {
    "human_operator_answer_recorded": False,
    "human_operator_approval_recorded": False,
    "product_family_selected_for_approval": False,
    "retail_reality_approved": False,
    "compliance_desk_delivery_authorized": False,
    "document_handoff_approved": False,
    "incident_verification_approved": False,
    "local_data_collection_approved": False,
    "customer_copy_created": False,
    "customer_copy_ready": False,
    "customer_delivery_approved": False,
    "publication_approved": False,
    "public_route_ready": False,
    "catalog_route_ready": False,
    "pricing_or_customer_quote_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_ready": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "live_acontext_or_runtime_ready": False,
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "irc_session_manager_mutated": False,
    "cross_project_autorouting_ready": False,
    "payment_or_production_reverified": False,
    "exact_gps_or_raw_metadata_release_allowed": False,
    "private_context_release_allowed": False,
    "domain_authority_claims_allowed": False,
    "worker_copyable_aas_doctrine_ready": False,
    "stopped_project_integration_ready": False,
}

PAUSE_BLOCKED_CLAIMS = [
    *BOARD_BLOCKED_CLAIMS,
    *GUARD_BLOCKED_CLAIMS,
    "product_fork_pause_human_answer_recorded",
    "product_fork_pause_human_approval_recorded",
    "product_fork_pause_selects_product_family_for_approval",
    "product_fork_pause_approves_retail_reality",
    "product_fork_pause_authorizes_compliance_desk_delivery",
    "product_fork_pause_approves_document_handoff",
    "product_fork_pause_approves_incident_verification",
    "product_fork_pause_approves_local_data_collection",
    "product_fork_pause_customer_copy_ready",
    "product_fork_pause_customer_delivery_approved",
    "product_fork_pause_publication_approved",
    "product_fork_pause_public_or_catalog_route_ready",
    "product_fork_pause_pricing_or_customer_quote_ready",
    "product_fork_pause_operator_queue_launch_ready",
    "product_fork_pause_dispatch_ready",
    "product_fork_pause_erc8004_reputation_ready",
    "product_fork_pause_worker_skill_dna_ready",
    "product_fork_pause_live_acontext_or_runtime_ready",
    "product_fork_pause_runtime_adapter_registration_or_enablement",
    "product_fork_pause_irc_session_manager_mutation",
    "product_fork_pause_cross_project_autorouting_ready",
    "product_fork_pause_payment_or_production_reverified",
    "product_fork_pause_exact_gps_or_raw_metadata_release_ready",
    "product_fork_pause_private_context_release_ready",
    "product_fork_pause_domain_authority_ready",
    "product_fork_pause_worker_copyable_doctrine_ready",
    "product_fork_pause_stopped_project_integration_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(PAUSE_BLOCKED_CLAIMS) | {
    "human_answer_recorded",
    "human_approval_recorded",
    "operator_approved",
    "retail_reality_approved",
    "compliance_desk_delivery_authorized",
    "document_handoff_approved",
    "incident_verification_approved",
    "local_data_collection_approved",
    "customer_copy_ready",
    "customer_delivery_approved",
    "publishable",
    "publication_approved",
    "public_route_ready",
    "catalog_ready",
    "pricing_ready",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "runtime_adapter_registered",
    "runtime_adapter_enabled",
    "irc_session_manager_mutated",
    "cross_project_autorouting_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "private_context_release_ready",
    "legal_or_regulator_authority_ready",
    "emergency_response",
    "safety_certification",
    "repair_diagnosis",
    "insurance_adjustment",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
}

ROW_FALSE_FLAGS = [
    "this_pause_board_approves_family",
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



def _stable_digest(payload: Any) -> str:
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



def _assert_source_board_conservative(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_PORTFOLIO_NEXT_GATE_BOARD_SCHEMA:
        raise CityOpsContractError("Product fork pause source board schema drift")
    if board.get("board_id") != BOARD_ID:
        raise CityOpsContractError("Product fork pause source board id drift")
    if board.get("board_status") != BOARD_STATUS:
        raise CityOpsContractError("Product fork pause source board promoted")
    if AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM not in board.get("safe_to_claim", []):
        raise CityOpsContractError("Product fork pause source board safe claim missing")
    if board.get("default_decision", {}).get("if_no_human_authorization") != (
        "do_not_promote_any_family_keep_portfolio_ledger_read_only"
    ):
        raise CityOpsContractError("Product fork pause source board no-human default drift")
    if board.get("summary", {}).get("gates_ready_without_separate_authorization") != 0:
        raise CityOpsContractError("Product fork pause source board gained no-auth gates")

    forbidden_safe = set(board.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Product fork pause source board forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(BOARD_BLOCKED_CLAIMS) - set(board.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"Product fork pause source board missing blocked claims: {sorted(missing_blocked)}"
        )

    rows = board.get("next_gate_rows", [])
    if len(rows) != 5:
        raise CityOpsContractError("Product fork pause source board row count drift")
    ranks = [row.get("rank") for row in rows]
    if ranks != [1, 2, 3, 4, 5]:
        raise CityOpsContractError("Product fork pause source board rank drift")

    for flag in BOARD_FALSE_FLAGS:
        if board.get(flag) is not False:
            raise CityOpsContractError(f"Product fork pause source board promoted {flag}")
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
                    f"Product fork pause source board row promoted {row.get('family_id')} {flag}"
                )



def _assert_retail_hold_guard_conservative(guard: dict[str, Any]) -> None:
    if guard.get("schema") != RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SCHEMA:
        raise CityOpsContractError("Product fork pause retail guard schema drift")
    if guard.get("guard_id") != GUARD_ID:
        raise CityOpsContractError("Product fork pause retail guard id drift")
    if guard.get("guard_status") != GUARD_STATUS:
        raise CityOpsContractError("Product fork pause retail guard promoted")
    if guard.get("candidate_key") != "retail_reality_as_a_service":
        raise CityOpsContractError("Product fork pause retail guard candidate drift")
    if guard.get("no_human_answer_default") != "keep_all_product_forks_internal_admin_only":
        raise CityOpsContractError("Product fork pause retail guard no-human default drift")
    if RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM not in guard.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Product fork pause retail guard safe claim missing")

    forbidden_safe = set(guard.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Product fork pause retail guard forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(GUARD_BLOCKED_CLAIMS) - set(guard.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"Product fork pause retail guard missing blocked claims: {sorted(missing_blocked)}"
        )
    for flag in GUARD_FALSE_FLAGS:
        if guard.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Product fork pause retail guard readiness promoted {flag}")
        if guard.get("regression_assertions", {}).get(flag) is not False:
            raise CityOpsContractError(f"Product fork pause retail guard assertion promoted {flag}")



def _pause_row_from_source(row: dict[str, Any], *, retail_guard_digest: str) -> dict[str, Any]:
    family_id = row["family_id"]
    if family_id == "retail_reality_as_a_service":
        pause_action = "wait_for_real_operator_answer_or_keep_retail_boundary_held"
        source_guard = RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME
    elif family_id == "compliance_desk_as_a_service":
        pause_action = "keep_delivery_path_unauthorized_until_separate_operator_record_exists"
        source_guard = None
    else:
        pause_action = "continue_read_only_internal_prerequisite_review_only"
        source_guard = None

    pause_row: dict[str, Any] = {
        "rank": row["rank"],
        "family_id": family_id,
        "family_label": row["family_label"],
        "source_current_decision_posture": row["current_decision_posture"],
        "source_highest_safe_boundary": row["current_highest_safe_boundary"],
        "human_authorization_required": row["human_authorization_required"],
        "default_without_human": row["default_without_human"],
        "pause_action": pause_action,
        "explicit_human_answer_present": False,
        "approval_record_present": False,
        "customer_or_public_surface_allowed": False,
        "source_retail_hold_guard_digest_sha256": retail_guard_digest if source_guard else None,
        "source_retail_hold_guard_file": source_guard,
    }
    for flag in ROW_FALSE_FLAGS:
        pause_row[flag] = False
    return pause_row



def _assert_pause_board(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SCHEMA:
        raise CityOpsContractError("Product fork pause board schema drift")
    if board.get("pause_board_id") != PAUSE_BOARD_ID:
        raise CityOpsContractError("Product fork pause board id drift")
    if board.get("pause_board_status") != PAUSE_BOARD_STATUS:
        raise CityOpsContractError("Product fork pause board status promoted")
    if board.get("default_decision") != DEFAULT_DECISION:
        raise CityOpsContractError("Product fork pause board default decision drift")
    if board.get("runtime_decision") != RUNTIME_DECISION:
        raise CityOpsContractError("Product fork pause board runtime decision drift")
    if AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SAFE_CLAIM not in board.get("safe_to_claim", []):
        raise CityOpsContractError("Product fork pause board safe claim missing")

    forbidden_safe = set(board.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Product fork pause board forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(PAUSE_BLOCKED_CLAIMS) - set(board.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"Product fork pause board missing blocked claims: {sorted(missing_blocked)}"
        )
    if board.get("still_blocked_claims") != board.get("do_not_claim_yet"):
        raise CityOpsContractError("Product fork pause board blocked claims drift")

    for flag, expected in PAUSE_FALSE_FLAGS.items():
        if board.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"Product fork pause board readiness promoted {flag}")
        if board.get("regression_assertions", {}).get(flag) is not expected:
            raise CityOpsContractError(f"Product fork pause board assertion promoted {flag}")

    rows = board.get("product_family_pause_rows", [])
    if len(rows) != 5:
        raise CityOpsContractError("Product fork pause board row count drift")
    if rows[0].get("family_id") != "retail_reality_as_a_service":
        raise CityOpsContractError("Product fork pause board retail row drift")
    for row in rows:
        if row.get("explicit_human_answer_present") is not False:
            raise CityOpsContractError(f"Product fork pause board row answered {row.get('family_id')}")
        if row.get("approval_record_present") is not False:
            raise CityOpsContractError(f"Product fork pause board row approved {row.get('family_id')}")
        for flag in ROW_FALSE_FLAGS:
            if row.get(flag) is not False:
                raise CityOpsContractError(
                    f"Product fork pause board row promoted {row.get('family_id')} {flag}"
                )



def _load_source_next_gate_board(artifact_dir: str | Path | None = None) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME
    board = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(board, dict):
        raise CityOpsContractError("Product fork pause source board must be a JSON object")
    _assert_source_board_conservative(board)
    return board



def build_aas_product_fork_no_answer_pause_board(
    *,
    artifact_dir: str | Path | None = None,
    source_next_gate_board: dict[str, Any] | None = None,
    source_retail_hold_guard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin no-answer product-fork pause board."""

    board_source = source_next_gate_board or _load_source_next_gate_board(artifact_dir=artifact_dir)
    retail_guard = source_retail_hold_guard or load_retail_reality_product_exposure_hold_regression_guard(
        artifact_dir=artifact_dir
    )
    _assert_source_board_conservative(board_source)
    _assert_retail_hold_guard_conservative(retail_guard)

    do_not_claim_yet = _dedupe(
        [
            *board_source["do_not_claim_yet"],
            *retail_guard["do_not_claim_yet"],
            *PAUSE_BLOCKED_CLAIMS,
        ]
    )
    safe_to_claim = _dedupe(
        [
            AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM,
            RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM,
            AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SAFE_CLAIM,
        ]
    )

    retail_guard_digest = _stable_digest(retail_guard)
    pause_rows = [
        _pause_row_from_source(row, retail_guard_digest=retail_guard_digest)
        for row in board_source["next_gate_rows"]
    ]

    pause_board: dict[str, Any] = {
        "schema": AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_SCHEMA,
        "pause_board_id": PAUSE_BOARD_ID,
        "scope": SCOPE,
        "source_policy": SOURCE_POLICY,
        "pause_board_status": PAUSE_BOARD_STATUS,
        "source_artifacts": {
            "portfolio_next_gate_board": {
                "file": AAS_PORTFOLIO_NEXT_GATE_BOARD_FILENAME,
                "schema": board_source["schema"],
                "id": board_source["board_id"],
                "safe_claim": AAS_PORTFOLIO_NEXT_GATE_BOARD_SAFE_CLAIM,
                "digest_sha256": _stable_digest(board_source),
            },
            "retail_reality_product_exposure_hold_regression_guard": {
                "file": RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME,
                "schema": retail_guard["schema"],
                "id": retail_guard["guard_id"],
                "safe_claim": RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM,
                "digest_sha256": retail_guard_digest,
            },
        },
        "no_answer_state": {
            "explicit_human_operator_answer_present": False,
            "human_operator_approval_record_present": False,
            "product_family_approval_selected": False,
            "retail_reality_is_closest_review_candidate": True,
            "retail_reality_guard_confirms_hold": True,
            "no_human_default_applied": DEFAULT_DECISION,
            "runtime_decision_preserved": RUNTIME_DECISION,
        },
        "default_decision": DEFAULT_DECISION,
        "runtime_decision": RUNTIME_DECISION,
        "next_allowed_move": NEXT_ALLOWED_MOVE,
        "product_family_pause_rows": pause_rows,
        "allowed_without_human_answer": [
            "keep_all_product_forks_internal_admin_only",
            "display_this_pause_board_to_internal_admins",
            "continue_read_only_docs_or_fixture_review_only",
            "wait_for_separate_explicit_human_operator_answer_record",
        ],
        "forbidden_shortcuts": [
            "do_not_treat_next_gate_board_as_approval",
            "do_not_treat_retail_hold_guard_as_answer",
            "do_not_create_customer_copy_without_separate_approval",
            "do_not_mount_public_catalog_or_pricing_routes",
            "do_not_launch_operator_queue_or_dispatch",
            "do_not_attach_reputation_or_worker_skill_dna",
            "do_not_mutate_runtime_or_irc_session_manager",
            "do_not_use_stopped_projects_as_product_inputs",
        ],
        "regression_assertions": dict(PAUSE_FALSE_FLAGS),
        "readiness": dict(PAUSE_FALSE_FLAGS),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "still_blocked_claims": do_not_claim_yet,
        "blocked_claim_regression_count": len(do_not_claim_yet),
    }
    _assert_pause_board(pause_board)
    return pause_board



def write_aas_product_fork_no_answer_pause_board(artifact_dir: str | Path | None = None) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    pause_board = build_aas_product_fork_no_answer_pause_board(artifact_dir=target_dir)
    target_path = target_dir / AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME
    target_path.write_text(json.dumps(pause_board, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path



def load_aas_product_fork_no_answer_pause_board(
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_PRODUCT_FORK_NO_ANSWER_PAUSE_BOARD_FILENAME
    pause_board = json.loads(path.read_text(encoding="utf-8"))
    _assert_pause_board(pause_board)
    return pause_board
