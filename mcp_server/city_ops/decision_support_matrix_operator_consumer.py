"""Thin internal/operator consumer for the CaaS decision-support matrix route.

This module is intentionally smaller than a UI. It consumes only the authenticated
internal/admin route payload contract for ``GET /internal/admin/city-ops/decision-
support-matrix`` and packages the same sections as a deterministic operator/admin
consumer artifact. It must not reinterpret the card, publish a public route,
create customer copy, enable dispatch, write Acontext/memory, emit reputation, or
expose GPS/metadata.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .decision_support_matrix_admin_route import (
    INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH,
    INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_RESPONSE_INTERPRETATION,
    assert_internal_admin_decision_support_matrix_response_contract,
    load_internal_admin_decision_support_matrix_card,
)
from .proof_block_artifacts import _default_proof_block_dir

DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SCHEMA = (
    "city_ops.decision_support_matrix_operator_consumer.v1"
)
DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SAFE_CLAIM = (
    "decision_support_matrix_operator_consumer_landed"
)
DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME = (
    "decision_support_matrix_operator_consumer.json"
)

_FALSE_ACCESS_FLAGS = [
    "network_route_registered",
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

_FALSE_READINESS_FLAGS = [
    "operator_ui_ready",
    "polished_operator_console_ready",
    "public_route_ready",
    "customer_visible_catalog_ready",
    "customer_copy_ready",
    "dispatch_routing_ready",
    "dispatch_automation_ready",
    "live_acontext_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "legal_or_regulator_ready",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_municipal_doctrine_ready",
]

_ADDITIONAL_BLOCKED_CLAIMS = [
    "operator_ui_ready",
    "polished_operator_console_ready",
    "public_route_ready",
    "customer_visible_catalog_ready",
    "customer_copy_ready",
    "dispatch_routing_ready",
    "dispatch_automation_ready",
    "live_acontext_readiness",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "legal_sufficiency",
    "regulator_acceptance",
    "exact_gps_or_metadata_exposure",
    "worker_copyable_municipal_doctrine",
]


def build_decision_support_matrix_operator_consumer(
    *,
    artifact_dir: str | Path | None = None,
    route_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic consumer artifact from the internal/admin route card."""

    payload = route_payload or load_internal_admin_decision_support_matrix_card(
        artifact_dir=artifact_dir
    )
    assert_internal_admin_decision_support_matrix_response_contract(payload)

    safe_to_claim = _dedupe(
        [
            *payload["claim_boundaries"]["safe_to_claim"],
            DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *payload["claim_boundaries"]["do_not_claim_yet"],
            *_ADDITIONAL_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    consumer = {
        "schema": DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SCHEMA,
        "consumer_id": f"operator_consumer:{payload['card_id']}",
        "source_route": {
            "method": "GET",
            "path": INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH,
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            "source_card_id": payload["card_id"],
            "source_card_schema": payload["schema"],
            "source_payload_digest": _stable_digest(payload),
            "response_interpretation": (
                INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_RESPONSE_INTERPRETATION
            ),
            "consumes_only": [INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH],
            "forbidden_inputs": [
                "raw_transcript",
                "raw_conversation_replay",
                "raw_review_fixture",
                "unreviewed_memory",
                "freeform_worker_chat",
                "private_operator_context",
                "customer_copy_draft",
                "live_acontext_transport",
                "gps_or_metadata_payloads",
            ],
            "semantic_reinterpretation_performed": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            "network_route_registered": False,
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
            "render_status": "thin_internal_admin_consumer_landed_not_console",
            "layout": "internal_admin_passthrough_sections",
            "source_route_path": INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH,
            "network_route_registered": False,
            "allowed_interpretation": (
                INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_RESPONSE_INTERPRETATION
            ),
            "pass_through_sections": [
                "axis_cards",
                "claim_cards",
                "success_metrics",
                "readiness",
                "recommended_next_action",
                "next_smallest_proof",
            ],
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": {
            "operator_consumer_landed": True,
            "internal_admin_route_consumed": True,
            "route_payload_digest_verified": True,
            "operator_ui_ready": False,
            "polished_operator_console_ready": False,
            "public_route_ready": False,
            "customer_visible_catalog_ready": False,
            "customer_copy_ready": False,
            "dispatch_routing_ready": False,
            "dispatch_automation_ready": False,
            "live_acontext_ready": False,
            "acontext_sink_ready": False,
            "runtime_parity_proven": False,
            "erc8004_reputation_ready": False,
            "worker_skill_dna_ready": False,
            "legal_or_regulator_ready": False,
            "gps_or_metadata_exposure_allowed": False,
            "worker_copyable_municipal_doctrine_ready": False,
        },
        "operator_consumer_sections": {
            "axis_cards": [dict(item) for item in payload["axis_cards"]],
            "claim_cards": [dict(item) for item in payload["claim_cards"]],
            "success_metrics": dict(payload["success_metrics"]),
            "readiness": dict(payload["readiness"]),
            "recommended_next_action": payload["recommended_next_action"],
            "next_smallest_proof": list(payload["next_smallest_proof"]),
            "matrix_verdict": payload["matrix_verdict"],
            "card_verdict": payload["card_verdict"],
        },
        "consumer_verdict": (
            "operator_consumer_landed_internal_admin_only_no_external_readiness"
        ),
    }
    _assert_operator_consumer_conservative(consumer, payload)
    return consumer


def write_decision_support_matrix_operator_consumer_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic operator/admin consumer artifact."""

    consumer = build_decision_support_matrix_operator_consumer(
        artifact_dir=artifact_dir
    )
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME
    path.write_text(
        json.dumps(consumer, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_decision_support_matrix_operator_consumer(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted operator/admin consumer artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        consumer = json.load(fh)
    if not isinstance(consumer, dict):
        raise CityOpsContractError("operator consumer artifact must be an object")
    route_payload = load_internal_admin_decision_support_matrix_card(
        artifact_dir=base_dir
    )
    _assert_operator_consumer_conservative(consumer, route_payload)
    return consumer


def _assert_operator_consumer_conservative(
    consumer: dict[str, Any], route_payload: dict[str, Any]
) -> None:
    if consumer.get("schema") != DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SCHEMA:
        raise CityOpsContractError("operator consumer schema drift")

    source_route = consumer.get("source_route", {})
    if source_route.get("path") != INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH:
        raise CityOpsContractError("operator consumer source route drift")
    if source_route.get("method") != "GET":
        raise CityOpsContractError("operator consumer source method drift")
    if source_route.get("consumes_only") != [INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH]:
        raise CityOpsContractError("operator consumer must consume only the admin route")
    if source_route.get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError("operator consumer refuses semantic reinterpretation")
    if source_route.get("source_payload_digest") != _stable_digest(route_payload):
        raise CityOpsContractError("operator consumer source payload digest drift")

    access_policy = consumer.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("operator consumer audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("operator consumer requires admin context")
    for flag in _FALSE_ACCESS_FLAGS:
        if access_policy.get(flag) is not False:
            raise CityOpsContractError(f"operator consumer refuses access drift: {flag}")

    render_contract = consumer.get("render_contract", {})
    if render_contract.get("network_route_registered") is not False:
        raise CityOpsContractError("operator consumer must not register a network route")
    if render_contract.get("allowed_interpretation") != (
        INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_RESPONSE_INTERPRETATION
    ):
        raise CityOpsContractError("operator consumer interpretation drift")

    readiness = consumer.get("readiness", {})
    if readiness.get("operator_consumer_landed") is not True:
        raise CityOpsContractError("operator consumer landed flag missing")
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"operator consumer refuses readiness promotion: {flag}"
            )

    claim_boundaries = consumer.get("claim_boundaries", {})
    safe_to_claim = claim_boundaries.get("safe_to_claim")
    do_not_claim_yet = claim_boundaries.get("do_not_claim_yet")
    if not isinstance(safe_to_claim, list) or not isinstance(do_not_claim_yet, list):
        raise CityOpsContractError("operator consumer requires claim boundaries")
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)
    if DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("operator consumer safe claim missing")

    sections = consumer.get("operator_consumer_sections", {})
    for field in render_contract.get("pass_through_sections", []):
        if sections.get(field) != route_payload.get(field):
            raise CityOpsContractError(
                f"operator consumer pass-through section drift: {field}"
            )
    for field in ["matrix_verdict", "card_verdict"]:
        if sections.get(field) != route_payload.get(field):
            raise CityOpsContractError(f"operator consumer verdict drift: {field}")


def _assert_claim_boundaries(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"operator consumer refuses claim overlap: {overlap}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
