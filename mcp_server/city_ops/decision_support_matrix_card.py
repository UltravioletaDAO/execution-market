"""Internal/admin-only four-axis card for CaaS decision support.

This module renders the persisted decision-support readiness matrix as a
read-only operator/agent handoff card.  It deliberately consumes only the
matrix artifact and adds no new product interpretation: safe and blocked claims
remain adjacent, Acontext stays blocked/attemptable-but-not-ready, and the card
cannot become a public route, customer surface, dispatch router, memory writer,
reputation emitter, GPS/metadata surface, or worker-copyable doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .decision_support_readiness_matrix import (
    DECISION_SUPPORT_BLOCKED_CLAIMS,
    DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
    DECISION_SUPPORT_READINESS_MATRIX_SAFE_CLAIM,
    DECISION_SUPPORT_READINESS_MATRIX_SCHEMA,
    load_decision_support_readiness_matrix,
)
from .proof_block_artifacts import _default_proof_block_dir

DECISION_SUPPORT_MATRIX_CARD_SCHEMA = "city_ops.decision_support_matrix_card.v1"
DECISION_SUPPORT_MATRIX_CARD_SAFE_CLAIM = "decision_support_matrix_card_landed"
DECISION_SUPPORT_MATRIX_CARD_FILENAME = "decision_support_matrix_card.json"

DECISION_SUPPORT_MATRIX_CARD_BLOCKED_CLAIMS = [
    "public_route_ready",
    "customer_visible_catalog_ready",
    "customer_copy_ready",
    "polished_operator_console_ready",
    "operator_ui_ready",
    "dispatch_routing_ready",
    "dispatch_automation_ready",
    "live_acontext_readiness",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "acontext_live_write_completed",
    "acontext_live_retrieval_completed",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_municipal_doctrine",
    "legal_sufficiency",
    "regulator_acceptance",
    "exact_gps_or_metadata_exposure",
]

_FALSE_ACCESS_FLAGS = [
    "public_route_registered",
    "customer_visible",
    "worker_visible",
    "dispatch_enabled",
    "writes_live_acontext",
    "writes_municipal_memory",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_DERIVED_FLAGS = [
    "semantic_reinterpretation_performed",
    "reads_raw_transcripts",
    "reads_raw_review_fixtures",
    "reads_private_operator_context",
    "writes_customer_copy",
    "writes_live_acontext",
    "writes_municipal_memory",
    "enables_dispatch_automation",
    "emits_reputation_receipts",
    "publishes_worker_doctrine",
    "exposes_gps_or_metadata",
]

_FALSE_READINESS_FLAGS = [
    "matrix_card_promotes_readiness",
    "session_rebuild_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "live_acontext_ready",
    "dispatch_automation_ready",
    "customer_visible_catalog_ready",
    "public_route_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "legal_or_regulator_ready",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_municipal_doctrine_ready",
]


def build_decision_support_matrix_card(
    *,
    artifact_dir: str | Path | None = None,
    matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only internal/admin card from the persisted matrix.

    By default this loads the persisted `decision_support_readiness_matrix.json`.
    Tests may pass a matrix directly, but the same conservative checks run before
    a card is returned.
    """

    source_matrix = matrix or load_decision_support_readiness_matrix(
        artifact_dir=artifact_dir
    )
    _assert_matrix_mountable(source_matrix)

    safe_to_claim = _dedupe(
        [
            *source_matrix["claim_boundaries"]["safe_to_claim"],
            DECISION_SUPPORT_READINESS_MATRIX_SAFE_CLAIM,
            DECISION_SUPPORT_MATRIX_CARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_matrix["claim_boundaries"]["do_not_claim_yet"],
            *DECISION_SUPPORT_BLOCKED_CLAIMS,
            *DECISION_SUPPORT_MATRIX_CARD_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    card = {
        "schema": DECISION_SUPPORT_MATRIX_CARD_SCHEMA,
        "card_id": f"decision_support_matrix_card:{source_matrix['matrix_id']}",
        "source_matrix_id": source_matrix["matrix_id"],
        "proof_anchor_id": source_matrix["proof_anchor_id"],
        "coordination_session_id": source_matrix["coordination_session_id"],
        "compact_decision_id": source_matrix["compact_decision_id"],
        "review_packet_id": source_matrix["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [DECISION_SUPPORT_READINESS_MATRIX_FILENAME],
            "consumes_only": [DECISION_SUPPORT_READINESS_MATRIX_FILENAME],
            "forbidden_inputs": [
                "raw_transcript",
                "raw_conversation_replay",
                "raw_review_fixture",
                "unreviewed_memory",
                "freeform_worker_chat",
                "private_operator_context",
                "live_acontext_transport",
                "gps_or_metadata_payloads",
            ],
            "semantic_reinterpretation_performed": False,
            "reads_raw_transcripts": False,
            "reads_raw_review_fixtures": False,
            "reads_private_operator_context": False,
            "writes_customer_copy": False,
            "writes_live_acontext": False,
            "writes_municipal_memory": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "publishes_worker_doctrine": False,
            "exposes_gps_or_metadata": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            "public_route_registered": False,
            "customer_visible": False,
            "worker_visible": False,
            "dispatch_enabled": False,
            "writes_live_acontext": False,
            "writes_municipal_memory": False,
            "emits_reputation_receipts": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "render_contract": {
            "render_status": "internal_admin_four_axis_card_landed_not_public_route",
            "suggested_internal_path": "/internal/admin/city-ops/decision-support-matrix",
            "network_route_registered": False,
            "layout": "four_axis_matrix_card",
            "response_fields": [
                "axis_cards",
                "claim_cards",
                "success_metrics",
                "readiness",
                "recommended_next_action",
                "next_smallest_proof",
            ],
            "allowed_interpretation": "pass_through_matrix_fields_only",
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": {
            "matrix_card_landed": True,
            "matrix_card_promotes_readiness": False,
            "session_rebuild_ready": False,
            "acontext_sink_ready": False,
            "runtime_parity_proven": False,
            "live_acontext_ready": False,
            "dispatch_automation_ready": False,
            "customer_visible_catalog_ready": False,
            "public_route_ready": False,
            "erc8004_reputation_ready": False,
            "worker_skill_dna_ready": False,
            "legal_or_regulator_ready": False,
            "gps_or_metadata_exposure_allowed": False,
            "worker_copyable_municipal_doctrine_ready": False,
            "source_ready_to_attempt_live_transport": bool(
                source_matrix["readiness"].get("ready_to_attempt_live_transport")
            ),
        },
        "axis_cards": _axis_cards(source_matrix),
        "claim_cards": _claim_cards(safe_to_claim, do_not_claim_yet),
        "success_metrics": dict(source_matrix["success_metrics"]),
        "session_management_enhancements": [
            dict(item) for item in source_matrix["session_management_enhancements"]
        ],
        "recommended_next_action": source_matrix["recommended_next_action"],
        "matrix_verdict": source_matrix["matrix_verdict"],
        "card_verdict": _card_verdict(source_matrix),
        "next_smallest_proof": list(source_matrix["next_smallest_proof"]),
    }
    _assert_card_conservative(card, source_matrix)
    return card


def write_decision_support_matrix_card_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic decision-support matrix card fixture."""

    card = build_decision_support_matrix_card(artifact_dir=artifact_dir)
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / DECISION_SUPPORT_MATRIX_CARD_FILENAME
    path.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_decision_support_matrix_card(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted decision-support matrix card fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / DECISION_SUPPORT_MATRIX_CARD_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        card = json.load(fh)
    if not isinstance(card, dict):
        raise CityOpsContractError("decision support matrix card artifact must be an object")
    matrix = load_decision_support_readiness_matrix(artifact_dir=base_dir)
    _assert_card_conservative(card, matrix)
    return card


def _axis_cards(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": axis["axis"],
            "state": axis["state"],
            "ready_now": axis["ready_now"],
            "safe_use": axis["safe_use"],
            "blocked_until": axis["blocked_until"],
            "evidence": list(axis["evidence"]),
            "display_status": (
                "ready_for_operator_planning"
                if axis["ready_now"]
                else "blocked_or_attemptable_not_ready"
            ),
        }
        for axis in matrix["handoff_axes"]
    ]


def _claim_cards(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "card": "safe_to_claim",
            "status": "visible_without_softening",
            "values": list(safe_to_claim),
        },
        {
            "card": "do_not_claim_yet",
            "status": "visible_without_softening",
            "values": list(do_not_claim_yet),
        },
    ]


def _card_verdict(matrix: dict[str, Any]) -> str:
    if matrix["readiness"].get("ready_to_attempt_live_transport"):
        return "decision_support_matrix_card_landed_live_transport_attemptable_not_ready"
    return "decision_support_matrix_card_landed_live_transport_blocked"


def _assert_matrix_mountable(matrix: dict[str, Any]) -> None:
    if matrix.get("schema") != DECISION_SUPPORT_READINESS_MATRIX_SCHEMA:
        raise CityOpsContractError("decision support matrix card requires readiness matrix")
    derived_from = matrix.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("decision support matrix card requires read-only matrix")
    if derived_from.get("writes_live_sink") is not False:
        raise CityOpsContractError("decision support matrix card refuses live sink writes")
    if derived_from.get("raw_conversation_reopened") is not False:
        raise CityOpsContractError("decision support matrix card refuses raw conversation replay")
    if derived_from.get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError("decision support matrix card refuses reinterpretation")

    readiness = matrix.get("readiness", {})
    for flag in (
        "session_rebuild_ready",
        "acontext_sink_ready",
        "runtime_parity_proven",
        "worker_copyable_doctrine_ready",
    ):
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"decision support matrix card refuses promoted matrix readiness: {flag}"
            )
    _assert_claim_boundaries(
        matrix.get("claim_boundaries", {}).get("safe_to_claim", []),
        matrix.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_card_conservative(card: dict[str, Any], matrix: dict[str, Any]) -> None:
    if card.get("schema") != DECISION_SUPPORT_MATRIX_CARD_SCHEMA:
        raise CityOpsContractError("decision support matrix card schema drift")
    if card.get("source_matrix_id") != matrix.get("matrix_id"):
        raise CityOpsContractError("decision support matrix card source drift")

    derived_from = card.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("decision support matrix card source must be read-only")
    if derived_from.get("source_artifacts") != [DECISION_SUPPORT_READINESS_MATRIX_FILENAME]:
        raise CityOpsContractError("decision support matrix card source artifact drift")
    if derived_from.get("consumes_only") != [DECISION_SUPPORT_READINESS_MATRIX_FILENAME]:
        raise CityOpsContractError("decision support matrix card input drift")
    drifted_derived = [flag for flag in _FALSE_DERIVED_FLAGS if derived_from.get(flag) is not False]
    if drifted_derived:
        raise CityOpsContractError(
            f"decision support matrix card derived overclaims: {drifted_derived}"
        )

    access = card.get("access_policy", {})
    if access.get("audience") != "internal_admin_only":
        raise CityOpsContractError("decision support matrix card audience drift")
    if access.get("requires_admin_context") is not True:
        raise CityOpsContractError("decision support matrix card admin context drift")
    drifted_access = [flag for flag in _FALSE_ACCESS_FLAGS if access.get(flag) is not False]
    if drifted_access:
        raise CityOpsContractError(
            f"decision support matrix card access overclaims: {drifted_access}"
        )

    render_contract = card.get("render_contract", {})
    if render_contract.get("network_route_registered") is not False:
        raise CityOpsContractError("decision support matrix card route drift")
    if render_contract.get("allowed_interpretation") != "pass_through_matrix_fields_only":
        raise CityOpsContractError("decision support matrix card interpretation drift")

    readiness = card.get("readiness", {})
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"decision support matrix card promoted readiness: {flag}"
            )

    matrix_axes = matrix.get("handoff_axes", [])
    card_axes = card.get("axis_cards", [])
    if [axis.get("axis") for axis in matrix_axes] != [axis.get("card") for axis in card_axes]:
        raise CityOpsContractError("decision support matrix card axis drift")
    if len(matrix_axes) != len(card_axes):
        raise CityOpsContractError("decision support matrix card axis count drift")
    for source, rendered in zip(matrix_axes, card_axes):
        for field in ("state", "ready_now", "safe_use", "blocked_until"):
            if rendered.get(field) != source.get(field):
                raise CityOpsContractError(
                    f"decision support matrix card changed axis field: {field}"
                )
        if rendered.get("evidence") != source.get("evidence"):
            raise CityOpsContractError("decision support matrix card changed axis evidence")

    _assert_claim_boundaries(
        card.get("claim_boundaries", {}).get("safe_to_claim", []),
        card.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_claim_boundaries(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> None:
    blocked_safe = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if blocked_safe:
        raise CityOpsContractError(
            f"decision support matrix card blocked claims safe: {blocked_safe}"
        )
    forbidden_safe = sorted(
        set(safe_to_claim)
        & (set(DECISION_SUPPORT_BLOCKED_CLAIMS) | set(DECISION_SUPPORT_MATRIX_CARD_BLOCKED_CLAIMS))
    )
    if forbidden_safe:
        raise CityOpsContractError(
            f"decision support matrix card forbidden safe claims: {forbidden_safe}"
        )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped
