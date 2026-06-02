"""Retail Reality product-exposure hold regression guard.

This module adds a read-only, no-human-answer regression guard after the Retail
Reality product-exposure boundary packet. It consumes exactly one internal/admin
packet and proves that the packet still cannot be interpreted as approval,
customer exposure, public/catalog readiness, pricing, queue launch, dispatch,
reputation, runtime mutation, payment/production proof, location/raw-metadata
release, retail/domain authority, or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .retail_reality_fixture_review_gate import ARTIFACT_DIR
from .retail_reality_product_exposure_boundary_packet import (
    PACKET_BLOCKED_CLAIMS,
    PACKET_FALSE_FLAGS,
    PACKET_ID,
    RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME,
    RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM,
    RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SCHEMA,
    load_retail_reality_product_exposure_boundary_packet,
)

RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SCHEMA = (
    "city_ops.retail_reality_product_exposure_hold_regression_guard.v1"
)
RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME = (
    "retail_reality_product_exposure_hold_regression_guard.json"
)
RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM = (
    "retail_reality_product_exposure_hold_regression_guard_landed"
)

GUARD_ID = "execution_market.aas.retail_reality.product_exposure_hold_regression_guard.001"
SCOPE = "internal_admin_no_human_answer_product_exposure_hold_regression_only"
GUARD_STATUS = "read_only_regression_guard_no_answer_no_approval_no_exposure"
SOURCE_POLICY = "consume_only_retail_reality_product_exposure_boundary_packet_json"
NEXT_ALLOWED_MOVE = "wait_for_explicit_human_operator_answer_or_keep_all_product_forks_held"

GUARD_FALSE_FLAGS = {
    "human_operator_answer_recorded": False,
    "human_operator_approval_recorded": False,
    "hold_record_created": False,
    "selected_boundary_approved": False,
    "product_exposure_approved": False,
    "customer_copy_created": False,
    "customer_copy_ready": False,
    "customer_delivery_approved": False,
    "publication_approved": False,
    "public_route_ready": False,
    "catalog_route_ready": False,
    "pricing_or_quote_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_ready": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "live_acontext_or_runtime_ready": False,
    "payment_or_production_reverified": False,
    "exact_gps_or_raw_metadata_release_allowed": False,
    "private_context_release_allowed": False,
    "retail_authority_claims_allowed": False,
    "worker_copyable_retail_doctrine_ready": False,
}

GUARD_BLOCKED_CLAIMS = [
    "retail_reality_product_exposure_hold_regression_human_answer_recorded",
    "retail_reality_product_exposure_hold_regression_human_approval_recorded",
    "retail_reality_product_exposure_hold_regression_hold_record_created",
    "retail_reality_product_exposure_hold_regression_selected_boundary_approved",
    "retail_reality_product_exposure_hold_regression_customer_copy_ready",
    "retail_reality_product_exposure_hold_regression_customer_delivery_approved",
    "retail_reality_product_exposure_hold_regression_publication_approved",
    "retail_reality_product_exposure_hold_regression_public_or_catalog_route_ready",
    "retail_reality_product_exposure_hold_regression_pricing_or_quote_ready",
    "retail_reality_product_exposure_hold_regression_operator_queue_launch_ready",
    "retail_reality_product_exposure_hold_regression_dispatch_ready",
    "retail_reality_product_exposure_hold_regression_erc8004_reputation_ready",
    "retail_reality_product_exposure_hold_regression_worker_skill_dna_ready",
    "retail_reality_product_exposure_hold_regression_live_acontext_or_runtime_ready",
    "retail_reality_product_exposure_hold_regression_payment_or_production_reverified",
    "retail_reality_product_exposure_hold_regression_exact_gps_or_raw_metadata_release_ready",
    "retail_reality_product_exposure_hold_regression_private_context_release_ready",
    "retail_reality_product_exposure_hold_regression_retail_authority_ready",
    "retail_reality_product_exposure_hold_regression_worker_copyable_retail_doctrine_ready",
]

FORBIDDEN_SAFE_CLAIMS = set(PACKET_BLOCKED_CLAIMS) | set(GUARD_BLOCKED_CLAIMS) | {
    "human_answer_recorded",
    "human_approval_recorded",
    "operator_approved",
    "selected_boundary_approved",
    "product_exposure_approved",
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
    "payment_production_reverified",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "private_context_release_ready",
    "retail_authority_ready",
    "worker_copyable_doctrine_ready",
}

SOURCE_MUST_STAY_FALSE = [
    *PACKET_FALSE_FLAGS.keys(),
    "human_operator_answer_recorded",
    "human_operator_approval_recorded",
    "selected_text_boundary_approved",
    "product_exposure_approved",
    "customer_delivery_authorized",
    "publication_approved",
    "public_route_registered",
    "catalog_route_registered",
    "pricing_enabled",
    "dispatch_enabled",
    "live_acontext_ready",
    "runtime_adapter_mutation_ready",
    "exact_gps_or_raw_metadata_release_allowed",
    "private_context_release_allowed",
    "retail_authority_claims_allowed",
    "worker_copyable_retail_doctrine_ready",
]

FORBIDDEN_NESTED_KEYS = {
    "candidate_text_values",
    "raw_gps",
    "raw_metadata",
    "exact_gps",
    "private_context",
    "worker_copyable_doctrine",
}


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


def _iter_nested_keys(payload: Any):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key
            yield from _iter_nested_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_nested_keys(item)


def _assert_source_packet(packet: dict[str, Any]) -> None:
    if packet.get("schema") != RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SCHEMA:
        raise CityOpsContractError("Retail Reality hold guard source schema drift")
    if packet.get("packet_id") != PACKET_ID:
        raise CityOpsContractError("Retail Reality hold guard source packet id drift")
    source_artifact = packet.get("source_artifact", {})
    if source_artifact.get("file") != "retail_reality_pending_approval_status_card.json":
        raise CityOpsContractError("Retail Reality hold guard source artifact drift")
    if packet.get("packet_status") != "prepared_for_human_review_not_submitted_not_approved_not_exposed":
        raise CityOpsContractError("Retail Reality hold guard source packet promoted")
    if packet.get("candidate_count") != 1:
        raise CityOpsContractError("Retail Reality hold guard source candidate count drift")
    if RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM not in packet.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Retail Reality hold guard source safe claim missing")

    source_safe = set(packet.get("claim_boundaries", {}).get("safe_to_claim", []))
    forbidden_safe = source_safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Retail Reality hold guard source forbidden safe claims: {sorted(forbidden_safe)}"
        )

    source_blocked = packet.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    missing_blocked = set(PACKET_BLOCKED_CLAIMS) - set(source_blocked)
    if missing_blocked:
        raise CityOpsContractError(
            f"Retail Reality hold guard source missing blocked claims: {sorted(missing_blocked)}"
        )
    if packet.get("still_blocked_claims") != source_blocked:
        raise CityOpsContractError("Retail Reality hold guard source blocked claims drift")

    for flag in _dedupe(SOURCE_MUST_STAY_FALSE):
        if flag in packet and packet[flag] is not False:
            raise CityOpsContractError(f"Retail Reality hold guard source promoted flag {flag}")
        if packet.get("readiness", {}).get(flag, False) is not False:
            raise CityOpsContractError(f"Retail Reality hold guard source readiness promoted {flag}")

    for flag in [
        "customer_visible",
        "catalog_visible",
        "pricing_enabled",
        "worker_visible",
        "dispatch_enabled",
        "writes_live_acontext",
        "mutates_runtime_adapter_or_session_manager",
        "emits_reputation_receipts",
        "exposes_exact_gps_or_raw_metadata",
        "exposes_private_context",
        "publishes_worker_doctrine",
    ]:
        if packet.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality hold guard source access promoted {flag}")

    leaked_keys = set(_iter_nested_keys(packet)) & FORBIDDEN_NESTED_KEYS
    if leaked_keys:
        raise CityOpsContractError(f"Retail Reality hold guard source leaked forbidden keys: {sorted(leaked_keys)}")


def _assert_guard(guard: dict[str, Any]) -> None:
    if guard.get("schema") != RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SCHEMA:
        raise CityOpsContractError("Retail Reality hold guard schema drift")
    if guard.get("guard_id") != GUARD_ID:
        raise CityOpsContractError("Retail Reality hold guard id drift")
    if guard.get("guard_status") != GUARD_STATUS:
        raise CityOpsContractError("Retail Reality hold guard status promoted")
    if guard.get("source_packet_id") != PACKET_ID:
        raise CityOpsContractError("Retail Reality hold guard source packet id mismatch")
    if guard.get("source_packet_filename") != RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME:
        raise CityOpsContractError("Retail Reality hold guard source filename mismatch")
    if RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM not in guard.get(
        "safe_to_claim", []
    ):
        raise CityOpsContractError("Retail Reality hold guard safe claim missing")

    forbidden_safe = set(guard.get("safe_to_claim", [])) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Retail Reality hold guard forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(GUARD_BLOCKED_CLAIMS) - set(guard.get("do_not_claim_yet", []))
    if missing_blocked:
        raise CityOpsContractError(
            f"Retail Reality hold guard missing blocked claims: {sorted(missing_blocked)}"
        )
    if guard.get("still_blocked_claims") != guard.get("do_not_claim_yet"):
        raise CityOpsContractError("Retail Reality hold guard blocked claims drift")

    for flag in GUARD_FALSE_FLAGS:
        if guard.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality hold guard readiness promoted {flag}")
        if guard.get("regression_assertions", {}).get(flag) is not False:
            raise CityOpsContractError(f"Retail Reality hold guard assertion promoted {flag}")

    if guard.get("next_allowed_move") != NEXT_ALLOWED_MOVE:
        raise CityOpsContractError("Retail Reality hold guard next move drift")


def build_retail_reality_product_exposure_hold_regression_guard(
    *,
    source_packet: dict[str, Any] | None = None,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    packet = source_packet or load_retail_reality_product_exposure_boundary_packet(
        artifact_dir=artifact_dir
    )
    _assert_source_packet(packet)

    do_not_claim_yet = _dedupe(
        [
            *packet["claim_boundaries"]["do_not_claim_yet"],
            *GUARD_BLOCKED_CLAIMS,
        ]
    )
    safe_to_claim = _dedupe(
        [
            RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM,
            RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM,
        ]
    )

    guard = {
        "schema": RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SCHEMA,
        "guard_id": GUARD_ID,
        "scope": SCOPE,
        "source_policy": SOURCE_POLICY,
        "guard_status": GUARD_STATUS,
        "source_packet_filename": RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME,
        "source_packet_id": packet["packet_id"],
        "source_packet_safe_claim": RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM,
        "source_packet_digest_sha256": _stable_digest(packet),
        "candidate_count": packet["candidate_count"],
        "candidate_key": packet["aas_candidates"][0]["candidate_key"],
        "candidate_text_values_visible": False,
        "source_selected_boundary_digest_sha256": packet["aas_candidates"][0][
            "selected_text_boundary_digest_sha256"
        ],
        "regression_assertions": dict(GUARD_FALSE_FLAGS),
        "readiness": dict(GUARD_FALSE_FLAGS),
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "still_blocked_claims": do_not_claim_yet,
        "blocked_claim_regression_count": len(do_not_claim_yet),
        "next_allowed_move": NEXT_ALLOWED_MOVE,
        "no_human_answer_default": "keep_all_product_forks_internal_admin_only",
    }
    _assert_guard(guard)
    return guard


def write_retail_reality_product_exposure_hold_regression_guard(
    artifact_dir: str | Path | None = None,
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    guard = build_retail_reality_product_exposure_hold_regression_guard(artifact_dir=target_dir)
    target_path = target_dir / RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME
    target_path.write_text(json.dumps(guard, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path


def load_retail_reality_product_exposure_hold_regression_guard(
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME
    guard = json.loads(path.read_text(encoding="utf-8"))
    _assert_guard(guard)
    return guard
