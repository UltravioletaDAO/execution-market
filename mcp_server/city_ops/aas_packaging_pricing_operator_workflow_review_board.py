"""Internal AAS packaging/pricing/operator-workflow review board.

This module is the no-customer-exposure follow-up to the three-family
packaging review packet. It consumes only the persisted
``aas_three_family_packaging_review_packet.json`` artifact and turns package
labels, pricing inputs, and operator workflow/queue questions into an
internal/admin review board. It does not approve customer copy, publication,
public prices or customer quotes, routes, pilots, dispatch, reputation, live
Acontext/runtime parity, exact GPS/raw metadata release, domain authority, or
worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_three_family_packaging_review_packet import (
    AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME,
    AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM,
    AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SCHEMA,
    PACKET_BLOCKED_CLAIMS,
    PACKET_ID,
    READINESS_FALSE_FLAGS as SOURCE_READINESS_FALSE_FLAGS,
    REVIEW_MODE as SOURCE_REVIEW_MODE,
    SOURCE_DECISION_SPECS,
    load_aas_three_family_packaging_review_packet,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SCHEMA = (
    "city_ops.aas_packaging_pricing_operator_workflow_review_board.v1"
)
AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME = (
    "aas_packaging_pricing_operator_workflow_review_board.json"
)
AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SAFE_CLAIM = (
    "aas_packaging_pricing_operator_workflow_review_board_landed"
)

BOARD_ID = "execution_market.aas.packaging_pricing_operator_workflow_review_board.001"
SCOPE = "internal_admin_review_board_only_no_customer_exposure"
SOURCE_POLICY = "consume_only_persisted_aas_three_family_packaging_review_packet_json"

BOARD_READINESS_FALSE_FLAGS = [
    *SOURCE_READINESS_FALSE_FLAGS,
    "package_label_approved_for_customer_copy",
    "pricing_model_approved",
    "public_price_approved",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "operator_workflow_launch_ready",
    "public_route_registered",
    "pilot_authorized",
    "domain_authority_approved",
]

REQUIRED_BLOCKED_CLAIMS = [
    *PACKET_BLOCKED_CLAIMS,
    "package_label_customer_copy_ready",
    "pricing_model_approved",
    "public_price_approved",
    "customer_quote_ready",
    "operator_queue_launch_ready",
    "operator_workflow_launch_ready",
    "public_route_registered",
    "pilot_authorized",
    "controlled_pilot_authorized",
    "dispatch_workflow_ready",
    "reputation_receipts_attachable",
    "live_runtime_ready",
    "gps_or_raw_metadata_release_ready",
    "domain_authority_approved",
    "worker_doctrine_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(REQUIRED_BLOCKED_CLAIMS) | {
    "customer_copy",
    "customer_copy_ready",
    "customer_output_ready",
    "customer_delivery_approval",
    "customer_delivery_ready",
    "publishable",
    "publication_ready",
    "catalog_ready",
    "public_route_ready",
    "route_ready",
    "pilot_ready",
    "dispatch_ready",
    "reputation_ready",
    "live_acontext_ready",
    "runtime_parity_proven",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
    "public_price_ready",
    "customer_quote_ready",
}

REQUIRED_SOURCE_FORBIDDEN_BOUNDARIES = {
    "publish customer copy",
    "quote a customer/public price",
    "mount catalog or public routes",
    "authorize controlled pilot exposure",
    "dispatch workers from this packet",
    "attach ERC-8004 reputation receipts",
    "claim live Acontext/runtime parity",
    "release exact GPS/raw metadata",
    "create worker-copyable doctrine",
}

REQUIRED_PRICE_OUTPUT_BLOCKS = {
    "public_price",
    "customer_quote",
    "front_door_sku",
    "sla_or_guaranteed_outcome_price",
}

REQUIRED_OPERATOR_FALSE_FLAGS = {
    "launch_not_authorized": True,
    "customer_delivery_path_authorized": False,
    "worker_dispatch_path_authorized": False,
}


def _canonical_digest(payload: dict[str, Any]) -> str:
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


def _load_source_packet(artifact_dir: Path | None = None) -> dict[str, Any]:
    return load_aas_three_family_packaging_review_packet(artifact_dir=artifact_dir)


def _assert_source_packet(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SCHEMA:
        raise CityOpsContractError("review board source packet schema drift")
    if packet.get("packet_id") != PACKET_ID:
        raise CityOpsContractError("review board source packet id drift")
    if packet.get("review_mode") != SOURCE_REVIEW_MODE:
        raise CityOpsContractError("review board source packet mode drift")
    if AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM not in packet.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("review board source packet safe claim missing")
    forbidden_safe = set(packet.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"review board source packet forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(PACKET_BLOCKED_CLAIMS) - set(packet.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"review board source packet missing blocked claims: {sorted(missing_blocked)}"
        )
    for flag in SOURCE_READINESS_FALSE_FLAGS:
        if packet.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"review board source packet promoted readiness {flag}")
    summary = packet.get("summary", {})
    required_summary_true = [
        "all_families_at_explicit_hold_decision",
        "all_customer_delivery_blocked",
        "all_publication_blocked",
        "all_dispatch_and_reputation_blocked",
    ]
    for flag in required_summary_true:
        if summary.get(flag) is not True:
            raise CityOpsContractError(f"review board source packet summary drift {flag}")
    if summary.get("families_reviewed") != 3:
        raise CityOpsContractError("review board source packet family count drift")
    if [row.get("key") for row in packet.get("review_rows", [])] != [
        spec["key"] for spec in SOURCE_DECISION_SPECS
    ]:
        raise CityOpsContractError("review board source packet row order drift")
    source_decisions = packet.get("source_decisions", [])
    if len(source_decisions) != 3:
        raise CityOpsContractError("review board source decisions count drift")
    for decision in source_decisions:
        if decision.get("review_decision") != "hold_not_approved_not_publishable":
            raise CityOpsContractError("review board source decision promoted from hold")
        if decision.get("customer_delivery_approval") is not False:
            raise CityOpsContractError("review board source decision customer delivery promoted")
        if decision.get("publication_approved") is not False:
            raise CityOpsContractError("review board source decision publication promoted")
        if decision.get("promotion_allowed") is not False:
            raise CityOpsContractError("review board source decision ladder promoted")
    for row in packet.get("review_rows", []):
        if row.get("current_ladder_step") != "explicit_internal_admin_sample_output_hold_decision":
            raise CityOpsContractError("review board source row ladder drift")
        if row.get("packaging_state") != "internal_admin_package_candidate_only":
            raise CityOpsContractError("review board source row packaging promoted")
        if row.get("pricing_state") != (
            "pricing_inputs_reviewable_but_no_public_price_or_quote_approved"
        ):
            raise CityOpsContractError("review board source row pricing promoted")
        if row.get("operator_workflow_state") != (
            "queue_and_review_steps_discussable_but_not_launch_ready"
        ):
            raise CityOpsContractError("review board source row workflow promoted")
        for flag in SOURCE_READINESS_FALSE_FLAGS:
            if row.get("readiness", {}).get(flag) is not False:
                raise CityOpsContractError(
                    f"review board source row promoted readiness {flag}"
                )
    boundaries = packet.get("packaging_review_boundaries", {})
    missing_boundaries = REQUIRED_SOURCE_FORBIDDEN_BOUNDARIES - set(
        boundaries.get("forbidden", [])
    )
    if missing_boundaries:
        raise CityOpsContractError(
            f"review board source packet forbidden boundary drift: {sorted(missing_boundaries)}"
        )
    pricing_outputs = set(packet.get("pricing_review_inputs", {}).get("outputs_not_approved", []))
    missing_outputs = REQUIRED_PRICE_OUTPUT_BLOCKS - pricing_outputs
    if missing_outputs:
        raise CityOpsContractError(
            f"review board source packet price/customer quote block drift: {sorted(missing_outputs)}"
        )
    operator_workflow = packet.get("operator_workflow_review", {})
    for flag, expected in REQUIRED_OPERATOR_FALSE_FLAGS.items():
        if operator_workflow.get(flag) is not expected:
            raise CityOpsContractError(f"review board source packet operator workflow drift {flag}")


def _review_question_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": row["key"],
        "family_id": row["family_id"],
        "family_label": row["family_label"],
        "offer_id": row["offer_id"],
        "package_label_under_review": row["package_label_for_review"],
        "package_label_customer_copy_approved": False,
        "pricing_unit_under_review": row["pricing_review_unit"],
        "public_price_approved": False,
        "customer_quote_ready": False,
        "operator_queue_under_review": row["operator_queue_for_review"],
        "operator_queue_launch_ready": False,
        "workflow_questions": [
            {
                "question": "Does the package label describe the internal evidence boundary without becoming customer copy?",
                "status": "review_question_only_not_approved",
            },
            {
                "question": "Which pricing input drives operator effort: minutes, evidence count, media complexity, redaction complexity, or follow-on task triggers?",
                "status": "review_question_only_no_public_price_or_customer_quote",
            },
            {
                "question": "Which queue step needs a separate human approval artifact before any delivery path exists?",
                "status": "review_question_only_not_launch_ready",
            },
        ],
        "blocked_authority_class": row["blocked_authority_class"],
        "readiness": {flag: False for flag in BOARD_READINESS_FALSE_FLAGS},
        "still_held": True,
    }


def build_aas_packaging_pricing_operator_workflow_review_board(
    *,
    artifact_dir: Path | None = None,
    source_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the internal/admin review board from the persisted packet only."""

    packet = source_packet or _load_source_packet(artifact_dir=artifact_dir)
    _assert_source_packet(packet)

    board_rows = [_review_question_row(row) for row in packet["review_rows"]]
    safe_to_claim = _dedupe(
        [
            *packet.get("safe_to_claim", []),
            AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe([*REQUIRED_BLOCKED_CLAIMS, *packet.get("do_not_claim_yet", [])])

    board = {
        "schema": AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SCHEMA,
        "board_id": BOARD_ID,
        "scope": SCOPE,
        "source_policy": SOURCE_POLICY,
        "source_packet_file": AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME,
        "source_packet_schema": packet["schema"],
        "source_packet_id": packet["packet_id"],
        "source_packet_digest_sha256": _canonical_digest(packet),
        "source_safe_claim": AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM,
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "summary": {
            "families_on_board": 3,
            "source_consumed": "aas_three_family_packaging_review_packet.json_only",
            "all_rows_remain_held": True,
            "customer_copy_approved": False,
            "customer_delivery_approved": False,
            "publication_approved": False,
            "public_prices_or_customer_quotes_approved": False,
            "routes_pilots_dispatch_reputation_live_runtime_gps_worker_doctrine_approved": False,
            "recommended_use": (
                "Internal/admin board for package label, pricing-input, and operator queue/workflow questions only."
            ),
        },
        "review_rows": board_rows,
        "pricing_input_questions": {
            "status": "internal_inputs_reviewable_only_no_public_price_or_customer_quote",
            "approved_outputs": [],
            "blocked_outputs": [
                "public_price",
                "customer_quote",
                "front_door_sku",
                "SLA_or_guaranteed_outcome_price",
                "domain_authority_premium",
            ],
            "questions": [
                "What operator-minute band should be reviewed for each package label?",
                "Which evidence/media/redaction complexity inputs should be measured before any price exists?",
                "Which follow-on task trigger changes internal effort without implying a customer quote?",
            ],
        },
        "operator_workflow_questions": {
            "status": "queue_and_workflow_questions_only_not_launch_ready",
            "launch_not_authorized": True,
            "customer_delivery_path_authorized": False,
            "worker_dispatch_path_authorized": False,
            "queues_under_review": [row["operator_queue_under_review"] for row in board_rows],
            "questions": [
                "Which queue receives intake before evidence contract selection?",
                "Where does operator limitation/redaction review happen?",
                "What separate approval record would be required before any customer delivery path?",
            ],
        },
        "review_boundaries": {
            "allowed": [
                "review package labels as internal/admin labels",
                "review pricing inputs without producing public prices or customer quotes",
                "review operator queue names and workflow questions without launching queues",
                "choose one held text boundary for a possible future separate approval artifact",
            ],
            "forbidden": [
                "approve customer copy or customer delivery",
                "publish public prices or customer quotes",
                "register public routes or catalog entries",
                "authorize controlled pilots or front-door SKUs",
                "dispatch workers or create dispatch instructions",
                "attach reputation receipts",
                "claim live Acontext/runtime parity",
                "release exact GPS/raw metadata",
                "approve domain authority or legal/notarial/emergency/safety/repair/insurance/SLA/official-report claims",
                "create worker-copyable doctrine",
            ],
        },
        "readiness": {flag: False for flag in BOARD_READINESS_FALSE_FLAGS},
        "next_steps": [
            (
                "Use this board for internal package-label, pricing-input, and operator workflow review only."
            ),
            (
                "If customer exposure is later desired, create a separate human-operator approval artifact for exactly one held text boundary."
            ),
        ],
    }
    _assert_board(board)
    return board


def _assert_board(board: dict[str, Any]) -> None:
    if board.get("schema") != AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SCHEMA:
        raise CityOpsContractError("review board schema drift")
    if board.get("board_id") != BOARD_ID:
        raise CityOpsContractError("review board id drift")
    if board.get("scope") != SCOPE:
        raise CityOpsContractError("review board scope drift")
    if board.get("source_policy") != SOURCE_POLICY:
        raise CityOpsContractError("review board source policy drift")
    if board.get("source_packet_file") != AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME:
        raise CityOpsContractError("review board source packet file drift")
    if board.get("source_packet_schema") != AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SCHEMA:
        raise CityOpsContractError("review board source packet schema drift")
    if board.get("source_packet_id") != PACKET_ID:
        raise CityOpsContractError("review board source packet id drift")
    if board.get("source_safe_claim") != AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM:
        raise CityOpsContractError("review board source safe claim drift")
    if AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_SAFE_CLAIM not in board.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("review board safe claim missing")
    if AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM not in board.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("review board source packet safe claim missing")
    forbidden_safe = set(board.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(f"review board has forbidden safe claims: {sorted(forbidden_safe)}")
    missing_blocked = set(REQUIRED_BLOCKED_CLAIMS) - set(board.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(f"review board missing blocked claims: {sorted(missing_blocked)}")
    summary = board.get("summary", {})
    if summary.get("families_on_board") != 3:
        raise CityOpsContractError("review board family count drift")
    for flag in [
        "all_rows_remain_held",
        "customer_copy_approved",
        "customer_delivery_approved",
        "publication_approved",
        "public_prices_or_customer_quotes_approved",
        "routes_pilots_dispatch_reputation_live_runtime_gps_worker_doctrine_approved",
    ]:
        expected = True if flag == "all_rows_remain_held" else False
        if summary.get(flag) is not expected:
            raise CityOpsContractError(f"review board summary promotion drift {flag}")
    for flag in BOARD_READINESS_FALSE_FLAGS:
        if board.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"review board promoted readiness {flag}")
    rows = board.get("review_rows", [])
    if len(rows) != 3:
        raise CityOpsContractError("review board must contain exactly three rows")
    expected_keys = [spec["key"] for spec in SOURCE_DECISION_SPECS]
    if [row.get("key") for row in rows] != expected_keys:
        raise CityOpsContractError("review board row order drift")
    for row in rows:
        if row.get("package_label_customer_copy_approved") is not False:
            raise CityOpsContractError("review board package label promoted to customer copy")
        if row.get("public_price_approved") is not False:
            raise CityOpsContractError("review board public price promoted")
        if row.get("customer_quote_ready") is not False:
            raise CityOpsContractError("review board customer quote promoted")
        if row.get("operator_queue_launch_ready") is not False:
            raise CityOpsContractError("review board operator queue launch promoted")
        if row.get("still_held") is not True:
            raise CityOpsContractError("review board row stopped being held")
        for flag in BOARD_READINESS_FALSE_FLAGS:
            if row.get("readiness", {}).get(flag) is not False:
                raise CityOpsContractError(f"review board row promoted readiness {flag}")
    pricing = board.get("pricing_input_questions", {})
    if pricing.get("status") != "internal_inputs_reviewable_only_no_public_price_or_customer_quote":
        raise CityOpsContractError("review board pricing status drift")
    if pricing.get("approved_outputs") != []:
        raise CityOpsContractError("review board pricing approved output drift")
    missing_price_blocks = {
        "public_price",
        "customer_quote",
        "front_door_sku",
        "SLA_or_guaranteed_outcome_price",
        "domain_authority_premium",
    } - set(pricing.get("blocked_outputs", []))
    if missing_price_blocks:
        raise CityOpsContractError(
            f"review board price/customer quote/domain authority blocks missing: {sorted(missing_price_blocks)}"
        )
    workflow = board.get("operator_workflow_questions", {})
    if workflow.get("status") != "queue_and_workflow_questions_only_not_launch_ready":
        raise CityOpsContractError("review board operator workflow status drift")
    for flag, expected in REQUIRED_OPERATOR_FALSE_FLAGS.items():
        if workflow.get(flag) is not expected:
            raise CityOpsContractError(f"review board operator workflow promoted {flag}")
    required_forbidden = {
        "approve customer copy or customer delivery",
        "publish public prices or customer quotes",
        "register public routes or catalog entries",
        "authorize controlled pilots or front-door SKUs",
        "dispatch workers or create dispatch instructions",
        "attach reputation receipts",
        "claim live Acontext/runtime parity",
        "release exact GPS/raw metadata",
        "approve domain authority or legal/notarial/emergency/safety/repair/insurance/SLA/official-report claims",
        "create worker-copyable doctrine",
    }
    missing_forbidden = required_forbidden - set(
        board.get("review_boundaries", {}).get("forbidden", [])
    )
    if missing_forbidden:
        raise CityOpsContractError(
            f"review board forbidden boundary drift: {sorted(missing_forbidden)}"
        )


def write_aas_packaging_pricing_operator_workflow_review_board(
    artifact_dir: Path | None = None,
) -> Path:
    target_dir = artifact_dir or ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    board = build_aas_packaging_pricing_operator_workflow_review_board(
        artifact_dir=target_dir
    )
    path = target_dir / AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME
    path.write_text(json.dumps(board, indent=2) + "\n", encoding="utf-8")
    return path


def load_aas_packaging_pricing_operator_workflow_review_board(
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    source_dir = artifact_dir or ARTIFACT_DIR
    path = source_dir / AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        board = json.load(fh)
    _assert_board(board)
    return board
