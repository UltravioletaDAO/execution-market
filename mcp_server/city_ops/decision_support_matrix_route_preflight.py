"""Fail-closed route preflight for the CaaS decision-support matrix card.

This module does not register a route.  It consumes the persisted
`decision_support_matrix_card.json` payload and emits a conservative preflight
artifact describing whether it would be safe to mount that card behind a real
authenticated internal/admin route.  The default state is intentionally blocked:
admin auth, payload parity, and no-interpretation response checks must all be
proven before a route can be considered mount-ready.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .decision_support_matrix_card import (
    DECISION_SUPPORT_MATRIX_CARD_BLOCKED_CLAIMS,
    DECISION_SUPPORT_MATRIX_CARD_FILENAME,
    DECISION_SUPPORT_MATRIX_CARD_SAFE_CLAIM,
    DECISION_SUPPORT_MATRIX_CARD_SCHEMA,
    load_decision_support_matrix_card,
)
from .proof_block_artifacts import _default_proof_block_dir

DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_SCHEMA = (
    "city_ops.decision_support_matrix_route_preflight.v1"
)
DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_SAFE_CLAIM = (
    "decision_support_matrix_route_preflight_landed"
)
DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_FILENAME = (
    "decision_support_matrix_route_preflight.json"
)

DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_BLOCKED_CLAIMS = [
    "authenticated_internal_admin_route_ready",
    "route_mount_ready",
    "route_response_verified",
    "admin_auth_boundary_proven",
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
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_municipal_doctrine",
    "legal_sufficiency",
    "regulator_acceptance",
    "exact_gps_or_metadata_exposure",
]

_FALSE_ROUTE_FLAGS = [
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
    "public_route_ready",
    "customer_visible_catalog_ready",
    "customer_copy_ready",
    "polished_operator_console_ready",
    "operator_ui_ready",
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


def build_decision_support_matrix_route_preflight(
    *,
    artifact_dir: str | Path | None = None,
    card: dict[str, Any] | None = None,
    route_probe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed route-readiness preflight over the matrix card."""

    source_card = card or load_decision_support_matrix_card(artifact_dir=artifact_dir)
    _assert_card_mountable(source_card)
    probe = _normalized_route_probe(source_card, route_probe)

    route_mount_ready = _route_mount_ready(probe)

    safe_to_claim = _dedupe(
        [
            *source_card["claim_boundaries"]["safe_to_claim"],
            DECISION_SUPPORT_MATRIX_CARD_SAFE_CLAIM,
            DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_card["claim_boundaries"]["do_not_claim_yet"],
            *DECISION_SUPPORT_MATRIX_CARD_BLOCKED_CLAIMS,
            *DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    preflight = {
        "schema": DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_SCHEMA,
        "preflight_id": f"decision_support_matrix_route_preflight:{source_card['card_id']}",
        "source_card_id": source_card["card_id"],
        "source_matrix_id": source_card["source_matrix_id"],
        "proof_anchor_id": source_card["proof_anchor_id"],
        "coordination_session_id": source_card["coordination_session_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [DECISION_SUPPORT_MATRIX_CARD_FILENAME],
            "consumes_only": [DECISION_SUPPORT_MATRIX_CARD_FILENAME],
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
            "writes_customer_copy": False,
            "writes_live_acontext": False,
            "writes_municipal_memory": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "publishes_worker_doctrine": False,
            "exposes_gps_or_metadata": False,
        },
        "route_contract": {
            "method": "GET",
            "suggested_internal_path": source_card["render_contract"][
                "suggested_internal_path"
            ],
            "allowed_interpretation": "pass_through_matrix_fields_only",
            "required_response_source": DECISION_SUPPORT_MATRIX_CARD_FILENAME,
            "required_response_fields": list(source_card["render_contract"]["response_fields"]),
            "route_registered_by_this_slice": False,
        },
        "route_probe": probe,
        "checks": {
            "admin_auth_boundary_present": probe["admin_auth_boundary_present"],
            "internal_path_matches_contract": probe["internal_path_matches_contract"],
            "card_payload_parity_verified": probe["card_payload_parity_verified"],
            "response_no_interpretation_verified": probe[
                "response_no_interpretation_verified"
            ],
            "external_side_effects_absent": all(
                probe[flag] is False for flag in _FALSE_ROUTE_FLAGS
            ),
            "route_handler_registered": probe["route_handler_registered"],
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            "public_route_registered": probe["public_route_registered"],
            "customer_visible": probe["customer_visible"],
            "worker_visible": probe["worker_visible"],
            "dispatch_enabled": probe["dispatch_enabled"],
            "writes_live_acontext": probe["writes_live_acontext"],
            "writes_municipal_memory": probe["writes_municipal_memory"],
            "emits_reputation_receipts": probe["emits_reputation_receipts"],
            "exposes_gps_or_metadata": probe["exposes_gps_or_metadata"],
            "publishes_worker_doctrine": probe["publishes_worker_doctrine"],
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": {
            "route_preflight_landed": True,
            "route_mount_ready": route_mount_ready,
            "authenticated_internal_admin_route_ready": route_mount_ready,
            "route_response_verified": route_mount_ready,
            "admin_auth_boundary_proven": probe["admin_auth_boundary_present"],
            "card_payload_parity_verified": probe["card_payload_parity_verified"],
            "response_no_interpretation_verified": probe[
                "response_no_interpretation_verified"
            ],
            "source_card_landed": True,
            "source_ready_to_attempt_live_transport": source_card["readiness"][
                "source_ready_to_attempt_live_transport"
            ],
            "public_route_ready": False,
            "customer_visible_catalog_ready": False,
            "customer_copy_ready": False,
            "polished_operator_console_ready": False,
            "operator_ui_ready": False,
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
        "preflight_verdict": (
            "decision_support_matrix_route_preflight_mount_ready_internal_admin_only"
            if route_mount_ready
            else "decision_support_matrix_route_preflight_blocked_until_admin_auth_and_parity"
        ),
        "next_smallest_proof": (
            "Implement the real authenticated internal/admin route only after this preflight proves admin auth, "
            "card payload parity, pass-through-only response semantics, and no external side effects. The route "
            "must return the persisted card payload as-is and must not add customer copy, dispatch, live Acontext "
            "writes, ERC-8004 reputation, worker Skill DNA, legal/regulator claims, GPS/metadata exposure, or "
            "worker-copyable doctrine."
        ),
    }
    _assert_preflight_conservative(preflight, source_card)
    return preflight


def write_decision_support_matrix_route_preflight_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic route-preflight fixture."""

    preflight = build_decision_support_matrix_route_preflight(artifact_dir=artifact_dir)
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_FILENAME
    path.write_text(json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_decision_support_matrix_route_preflight(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted route-preflight fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        preflight = json.load(fh)
    if not isinstance(preflight, dict):
        raise CityOpsContractError("decision support matrix route preflight must be an object")
    card = load_decision_support_matrix_card(artifact_dir=base_dir)
    _assert_preflight_conservative(preflight, card)
    return preflight


def _normalized_route_probe(
    card: dict[str, Any], route_probe: dict[str, Any] | None
) -> dict[str, Any]:
    probe = dict(route_probe or {})
    expected_path = card["render_contract"]["suggested_internal_path"]
    response_interpretation = probe.get("response_interpretation", "not_mounted")
    normalized = {
        "route_handler_registered": bool(probe.get("route_handler_registered", False)),
        "admin_auth_boundary_present": bool(
            probe.get("admin_auth_boundary_present", False)
        ),
        "route_path": probe.get("route_path", expected_path),
        "internal_path_matches_contract": probe.get("route_path", expected_path)
        == expected_path,
        "card_payload_parity_verified": bool(
            probe.get("card_payload_parity_verified", False)
        ),
        "response_interpretation": response_interpretation,
        "response_no_interpretation_verified": response_interpretation
        == "pass_through_matrix_fields_only",
    }
    for flag in _FALSE_ROUTE_FLAGS:
        normalized[flag] = bool(probe.get(flag, False))
    return normalized


def _route_mount_ready(probe: dict[str, Any]) -> bool:
    return (
        probe["route_handler_registered"]
        and probe["admin_auth_boundary_present"]
        and probe["internal_path_matches_contract"]
        and probe["card_payload_parity_verified"]
        and probe["response_no_interpretation_verified"]
        and all(probe[flag] is False for flag in _FALSE_ROUTE_FLAGS)
    )


def _assert_card_mountable(card: dict[str, Any]) -> None:
    if card.get("schema") != DECISION_SUPPORT_MATRIX_CARD_SCHEMA:
        raise CityOpsContractError("route preflight requires decision support matrix card")
    derived_from = card.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("route preflight requires read-only card")
    if derived_from.get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError("route preflight refuses interpreted card")
    access_policy = card.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("route preflight requires internal/admin-only card")
    for flag in _FALSE_ROUTE_FLAGS:
        if access_policy.get(flag) is not False:
            raise CityOpsContractError(f"route preflight refuses card access drift: {flag}")
    render_contract = card.get("render_contract", {})
    if render_contract.get("network_route_registered") is not False:
        raise CityOpsContractError("route preflight refuses already-registered route")
    if render_contract.get("allowed_interpretation") != "pass_through_matrix_fields_only":
        raise CityOpsContractError("route preflight refuses card interpretation drift")
    readiness = card.get("readiness", {})
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is True:
            raise CityOpsContractError(
                f"route preflight refuses promoted card readiness: {flag}"
            )


def _assert_preflight_conservative(
    preflight: dict[str, Any], card: dict[str, Any]
) -> None:
    if preflight.get("schema") != DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_SCHEMA:
        raise CityOpsContractError("invalid decision support matrix route preflight schema")
    if preflight.get("source_card_id") != card.get("card_id"):
        raise CityOpsContractError("route preflight source card mismatch")
    derived_from = preflight.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("route preflight must stay read-only")
    if derived_from.get("consumes_only") != [DECISION_SUPPORT_MATRIX_CARD_FILENAME]:
        raise CityOpsContractError("route preflight must consume only matrix card artifact")
    if derived_from.get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError("route preflight refuses semantic reinterpretation")

    access_policy = preflight.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("route preflight audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("route preflight requires admin context")
    for flag in _FALSE_ROUTE_FLAGS:
        if access_policy.get(flag) is not False:
            raise CityOpsContractError(f"route preflight refuses external route drift: {flag}")

    readiness = preflight.get("readiness", {})
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"route preflight refuses promoted readiness: {flag}"
            )
    if readiness.get("route_preflight_landed") is not True:
        raise CityOpsContractError("route preflight landed flag must be true")

    probe = preflight.get("route_probe", {})
    expected_ready = _route_mount_ready(probe)
    if readiness.get("route_mount_ready") is not expected_ready:
        raise CityOpsContractError("route mount readiness does not match preflight checks")
    if expected_ready:
        if readiness.get("authenticated_internal_admin_route_ready") is not True:
            raise CityOpsContractError("mount-ready preflight requires authenticated route readiness")
        if readiness.get("route_response_verified") is not True:
            raise CityOpsContractError("mount-ready preflight requires response verification")
    else:
        if preflight.get("preflight_verdict") != (
            "decision_support_matrix_route_preflight_blocked_until_admin_auth_and_parity"
        ):
            raise CityOpsContractError("blocked route preflight verdict drift")

    safe = preflight.get("claim_boundaries", {}).get("safe_to_claim", [])
    blocked = preflight.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    _assert_claim_boundaries(safe, blocked)


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"route preflight claim boundary overlap: {sorted(overlap)}")
    for claim in DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_BLOCKED_CLAIMS:
        if claim in safe_to_claim:
            raise CityOpsContractError(f"route preflight refuses blocked safe claim: {claim}")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
