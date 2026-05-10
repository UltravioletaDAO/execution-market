"""Data-only internal/admin display adapter for the CaaS matrix consumer.

This adapter is deliberately smaller than a UI, console, route, customer surface,
or dispatch tool.  It consumes only the persisted
``decision_support_matrix_operator_consumer.json`` artifact and reshapes the
already-approved consumer sections into deterministic display cards for internal
admin inspection.  It must not reinterpret matrix semantics, read raw evidence,
write Acontext/memory, emit reputation, expose GPS/metadata, or publish worker
copy.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .decision_support_matrix_operator_consumer import (
    DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME,
    DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SAFE_CLAIM,
    load_decision_support_matrix_operator_consumer,
)
from .proof_block_artifacts import _default_proof_block_dir

DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SCHEMA = (
    "city_ops.decision_support_matrix_operator_display_adapter.v1"
)
DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SAFE_CLAIM = (
    "decision_support_matrix_operator_display_adapter_landed"
)
DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME = (
    "decision_support_matrix_operator_display_adapter.json"
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

_FALSE_DERIVED_FLAGS = [
    "semantic_reinterpretation_performed",
    "reads_raw_transcripts",
    "reads_raw_review_fixtures",
    "reads_unreviewed_memory",
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
    "operator_ui_ready",
    "polished_operator_console_ready",
    "network_route_ready",
    "public_route_ready",
    "customer_visible_catalog_ready",
    "customer_copy_ready",
    "worker_visible_ready",
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
    "network_route_ready",
    "public_route_ready",
    "customer_visible_catalog_ready",
    "customer_copy_ready",
    "worker_visible_ready",
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

_DISPLAY_SECTION_FIELDS = [
    "axis_cards",
    "claim_cards",
    "success_metrics",
    "readiness",
    "recommended_next_action",
    "next_smallest_proof",
    "matrix_verdict",
    "card_verdict",
]


def build_decision_support_matrix_operator_display_adapter(
    *,
    artifact_dir: str | Path | None = None,
    operator_consumer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin display adapter payload."""

    consumer = operator_consumer or load_decision_support_matrix_operator_consumer(
        artifact_dir=artifact_dir
    )
    _assert_consumer_mountable(consumer)

    safe_to_claim = _dedupe(
        [
            *consumer["claim_boundaries"]["safe_to_claim"],
            DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SAFE_CLAIM,
            DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *consumer["claim_boundaries"]["do_not_claim_yet"],
            *_ADDITIONAL_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    sections = consumer["operator_consumer_sections"]
    adapter = {
        "schema": DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SCHEMA,
        "adapter_id": f"operator_display_adapter:{consumer['consumer_id']}",
        "source_consumer_id": consumer["consumer_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME],
            "consumes_only": [DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME],
            "source_consumer_digest": _stable_digest(consumer),
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
            "reads_raw_transcripts": False,
            "reads_raw_review_fixtures": False,
            "reads_unreviewed_memory": False,
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
        "display_contract": {
            "display_status": "data_only_internal_admin_adapter_landed_not_ui",
            "layout": "matrix_operator_cards",
            "network_route_registered": False,
            "operator_ui_ready": False,
            "polished_operator_console_ready": False,
            "allowed_interpretation": consumer["source_route"]["response_interpretation"],
            "pass_through_section_fields": list(_DISPLAY_SECTION_FIELDS),
            "display_cards_order": [
                "source_route",
                "axis_cards",
                "safe_to_claim",
                "do_not_claim_yet",
                "success_metrics",
                "readiness",
                "next_action",
            ],
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "display_cards": _display_cards(consumer, sections, safe_to_claim, do_not_claim_yet),
        "display_lines": _display_lines(sections, safe_to_claim, do_not_claim_yet),
        "readiness": {
            "display_adapter_landed": True,
            "operator_consumer_digest_verified": True,
            "data_only_internal_admin_adapter": True,
            "operator_ui_ready": False,
            "polished_operator_console_ready": False,
            "network_route_ready": False,
            "public_route_ready": False,
            "customer_visible_catalog_ready": False,
            "customer_copy_ready": False,
            "worker_visible_ready": False,
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
        "adapter_verdict": (
            "operator_display_adapter_landed_internal_admin_data_only_not_ui"
        ),
        "next_smallest_proof": [
            "If continuing, keep this adapter data-only or wire it to an authenticated internal/admin route that returns this payload as-is.",
            "Do not add customer copy, public route, dispatch automation, live Acontext writes, reputation, worker Skill DNA, GPS/metadata exposure, or worker-copyable doctrine.",
        ],
    }
    _assert_display_adapter_conservative(adapter, consumer)
    return adapter


def write_decision_support_matrix_operator_display_adapter_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic display adapter fixture."""

    adapter = build_decision_support_matrix_operator_display_adapter(
        artifact_dir=artifact_dir
    )
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME
    path.write_text(
        json.dumps(adapter, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_decision_support_matrix_operator_display_adapter(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted display adapter fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        adapter = json.load(fh)
    if not isinstance(adapter, dict):
        raise CityOpsContractError("operator display adapter artifact must be an object")
    consumer = load_decision_support_matrix_operator_consumer(artifact_dir=base_dir)
    _assert_display_adapter_conservative(adapter, consumer)
    return adapter


def _display_cards(
    consumer: dict[str, Any],
    sections: dict[str, Any],
    safe_to_claim: list[str],
    do_not_claim_yet: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "card": "source_route",
            "status": "internal_admin_route_consumer_preserved",
            "values": {
                "method": consumer["source_route"]["method"],
                "path": consumer["source_route"]["path"],
                "audience": consumer["source_route"]["audience"],
                "semantic_reinterpretation_performed": False,
            },
        },
        {
            "card": "axis_cards",
            "status": "visible_internal_admin_only",
            "values": [dict(axis) for axis in sections["axis_cards"]],
        },
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
        {
            "card": "success_metrics",
            "status": "pass_through",
            "values": dict(sections["success_metrics"]),
        },
        {
            "card": "readiness",
            "status": "pass_through_plus_adapter_false_readiness",
            "values": dict(sections["readiness"]),
        },
        {
            "card": "next_action",
            "status": "pass_through",
            "values": {
                "recommended_next_action": sections["recommended_next_action"],
                "next_smallest_proof": list(sections["next_smallest_proof"]),
            },
        },
    ]


def _display_lines(
    sections: dict[str, Any], safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> list[str]:
    return [
        f"matrix_verdict: {sections['matrix_verdict']}",
        f"card_verdict: {sections['card_verdict']}",
        f"axis_count: {len(sections['axis_cards'])}",
        f"safe_to_claim: {', '.join(safe_to_claim)}",
        f"do_not_claim_yet: {', '.join(do_not_claim_yet)}",
        f"recommended_next_action: {sections['recommended_next_action']}",
    ]


def _assert_consumer_mountable(consumer: dict[str, Any]) -> None:
    if not isinstance(consumer, dict):
        raise CityOpsContractError("operator display adapter requires consumer object")
    if DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SAFE_CLAIM not in consumer.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("operator display adapter requires consumer safe claim")
    if consumer.get("source_route", {}).get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError("operator display adapter refuses interpreted consumer")
    if consumer.get("access_policy", {}).get("audience") != "internal_admin_only":
        raise CityOpsContractError("operator display adapter audience drift")
    for flag in _FALSE_ACCESS_FLAGS:
        if consumer.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"operator display adapter refuses consumer access drift: {flag}"
            )
    for field in _DISPLAY_SECTION_FIELDS:
        if field not in consumer.get("operator_consumer_sections", {}):
            raise CityOpsContractError(
                f"operator display adapter missing consumer section: {field}"
            )


def _assert_display_adapter_conservative(
    adapter: dict[str, Any], consumer: dict[str, Any]
) -> None:
    if adapter.get("schema") != DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SCHEMA:
        raise CityOpsContractError("operator display adapter schema drift")
    if adapter.get("source_consumer_id") != consumer.get("consumer_id"):
        raise CityOpsContractError("operator display adapter source consumer drift")

    derived_from = adapter.get("derived_from", {})
    if derived_from.get("consumes_only") != [
        DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME
    ]:
        raise CityOpsContractError("operator display adapter must consume only consumer artifact")
    if derived_from.get("source_consumer_digest") != _stable_digest(consumer):
        raise CityOpsContractError("operator display adapter source consumer digest drift")
    for flag in _FALSE_DERIVED_FLAGS:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(
                f"operator display adapter refuses derived flag drift: {flag}"
            )

    access_policy = adapter.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("operator display adapter audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("operator display adapter requires admin context")
    for flag in _FALSE_ACCESS_FLAGS:
        if access_policy.get(flag) is not False:
            raise CityOpsContractError(
                f"operator display adapter refuses access drift: {flag}"
            )

    display_contract = adapter.get("display_contract", {})
    if display_contract.get("network_route_registered") is not False:
        raise CityOpsContractError("operator display adapter must not register a route")
    if display_contract.get("operator_ui_ready") is not False:
        raise CityOpsContractError("operator display adapter must not claim UI readiness")
    if display_contract.get("pass_through_section_fields") != _DISPLAY_SECTION_FIELDS:
        raise CityOpsContractError("operator display adapter pass-through field drift")

    readiness = adapter.get("readiness", {})
    if readiness.get("display_adapter_landed") is not True:
        raise CityOpsContractError("operator display adapter landed flag missing")
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"operator display adapter refuses readiness promotion: {flag}"
            )

    boundaries = adapter.get("claim_boundaries", {})
    safe_to_claim = boundaries.get("safe_to_claim")
    do_not_claim_yet = boundaries.get("do_not_claim_yet")
    if not isinstance(safe_to_claim, list) or not isinstance(do_not_claim_yet, list):
        raise CityOpsContractError("operator display adapter requires claim boundaries")
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)
    if DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("operator display adapter safe claim missing")

    cards = adapter.get("display_cards")
    if not isinstance(cards, list) or [card.get("card") for card in cards] != [
        "source_route",
        "axis_cards",
        "safe_to_claim",
        "do_not_claim_yet",
        "success_metrics",
        "readiness",
        "next_action",
    ]:
        raise CityOpsContractError("operator display adapter card order drift")

    expected_sections = consumer["operator_consumer_sections"]
    by_card = {card["card"]: card for card in cards}
    if by_card["axis_cards"].get("values") != expected_sections["axis_cards"]:
        raise CityOpsContractError("operator display adapter axis card drift")
    if by_card["success_metrics"].get("values") != expected_sections["success_metrics"]:
        raise CityOpsContractError("operator display adapter metrics card drift")
    if by_card["readiness"].get("values") != expected_sections["readiness"]:
        raise CityOpsContractError("operator display adapter readiness card drift")
    if by_card["safe_to_claim"].get("values") != safe_to_claim:
        raise CityOpsContractError("operator display adapter safe claim card drift")
    if by_card["do_not_claim_yet"].get("values") != do_not_claim_yet:
        raise CityOpsContractError("operator display adapter blocked claim card drift")


def _assert_claim_boundaries(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(
            f"operator display adapter refuses claim overlap: {overlap}"
        )


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
