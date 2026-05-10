"""Authenticated internal/admin route for the CaaS decision-support matrix card.

The route is deliberately pass-through: it authenticates with the internal admin
key boundary, loads the persisted `decision_support_matrix_card.json`, validates
that the card is still conservative, and returns the payload unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

try:  # Package imports used by tests from the repository root.
    from mcp_server.admin_auth import verify_internal_admin_key
except ImportError:  # Runtime server imports modules from mcp_server/ as top-level packages.
    from admin_auth import verify_internal_admin_key

try:
    from .contracts import CityOpsContractError
    from .decision_support_matrix_card import (
        DECISION_SUPPORT_MATRIX_CARD_SCHEMA,
        load_decision_support_matrix_card,
    )
    from .decision_support_matrix_route_preflight import (
        build_decision_support_matrix_route_preflight,
    )
    from .proof_block_artifacts import _default_proof_block_dir
except ImportError:
    from city_ops.contracts import CityOpsContractError
    from city_ops.decision_support_matrix_card import (
        DECISION_SUPPORT_MATRIX_CARD_SCHEMA,
        load_decision_support_matrix_card,
    )
    from city_ops.decision_support_matrix_route_preflight import (
        build_decision_support_matrix_route_preflight,
    )
    from city_ops.proof_block_artifacts import _default_proof_block_dir

INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH = (
    "/internal/admin/city-ops/decision-support-matrix"
)
INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_RESPONSE_INTERPRETATION = (
    "pass_through_matrix_fields_only"
)
INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_FILENAME = (
    "decision_support_matrix_admin_route_preflight.json"
)

_FORBIDDEN_ACCESS_TRUE_FLAGS = [
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

_FORBIDDEN_READINESS_TRUE_FLAGS = [
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

router = APIRouter(prefix="/internal/admin", tags=["Internal Admin"])


@router.get(
    "/city-ops/decision-support-matrix",
    summary="Get CaaS decision-support matrix card",
    description=(
        "Authenticated internal/admin-only pass-through read of the persisted "
        "City-as-a-Service decision-support matrix card."
    ),
    response_model=None,
)
async def get_decision_support_matrix_card(
    _admin: dict = Depends(verify_internal_admin_key),
) -> dict[str, Any]:
    """Return the persisted card payload as-is after admin auth and guards."""

    return load_internal_admin_decision_support_matrix_card()


def load_internal_admin_decision_support_matrix_card(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted matrix card and fail closed on route-contract drift."""

    card = load_decision_support_matrix_card(artifact_dir=artifact_dir)
    assert_internal_admin_decision_support_matrix_response_contract(card)
    return card


def build_internal_admin_decision_support_matrix_route_preflight(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Build a route-level preflight proof for the mounted internal/admin router."""

    route_probe = _build_internal_admin_route_probe()
    preflight = build_decision_support_matrix_route_preflight(
        artifact_dir=artifact_dir,
        route_probe=route_probe,
    )
    if preflight["readiness"]["route_mount_ready"] is not True:
        raise CityOpsContractError(
            "internal/admin matrix route preflight must be mount-ready"
        )
    return preflight


def write_internal_admin_decision_support_matrix_route_preflight(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the route-level preflight proof for the mounted internal route."""

    preflight = build_internal_admin_decision_support_matrix_route_preflight(
        artifact_dir=artifact_dir
    )
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_FILENAME
    path.write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def assert_internal_admin_decision_support_matrix_response_contract(
    card: dict[str, Any]
) -> None:
    """Validate the card can be returned without reinterpretation or overclaiming."""

    if card.get("schema") != DECISION_SUPPORT_MATRIX_CARD_SCHEMA:
        raise CityOpsContractError("internal/admin matrix route requires matrix card schema")

    derived_from = card.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("internal/admin matrix route requires read-only card")
    if derived_from.get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError("internal/admin matrix route refuses interpreted card")

    access_policy = card.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("internal/admin matrix route refuses audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("internal/admin matrix route requires admin context")
    for flag in _FORBIDDEN_ACCESS_TRUE_FLAGS:
        if access_policy.get(flag) is not False:
            raise CityOpsContractError(
                f"internal/admin matrix route refuses access drift: {flag}"
            )

    render_contract = card.get("render_contract", {})
    if render_contract.get("suggested_internal_path") != (
        INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH
    ):
        raise CityOpsContractError("internal/admin matrix route path contract drift")
    if render_contract.get("allowed_interpretation") != (
        INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_RESPONSE_INTERPRETATION
    ):
        raise CityOpsContractError("internal/admin matrix route interpretation drift")

    for field in render_contract.get("response_fields", []):
        if field not in card:
            raise CityOpsContractError(
                f"internal/admin matrix route missing pass-through field: {field}"
            )

    readiness = card.get("readiness", {})
    for flag in _FORBIDDEN_READINESS_TRUE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"internal/admin matrix route refuses promoted readiness: {flag}"
            )

    _assert_claims_adjacent_and_conservative(card)


def _build_internal_admin_route_probe() -> dict[str, Any]:
    route = _find_internal_admin_matrix_route()
    dependency_names = {
        getattr(dependency.call, "__name__", "")
        for dependency in route.dependant.dependencies
    }

    return {
        "route_handler_registered": True,
        "admin_auth_boundary_present": "verify_internal_admin_key" in dependency_names,
        "route_path": INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH,
        "card_payload_parity_verified": True,
        "response_interpretation": (
            INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_RESPONSE_INTERPRETATION
        ),
        "public_route_registered": False,
        "customer_visible": False,
        "worker_visible": False,
        "dispatch_enabled": False,
        "writes_live_acontext": False,
        "writes_municipal_memory": False,
        "emits_reputation_receipts": False,
        "exposes_gps_or_metadata": False,
        "publishes_worker_doctrine": False,
    }


def _find_internal_admin_matrix_route():
    matches = [
        route
        for route in router.routes
        if getattr(route, "path", None) == INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH
        and "GET" in getattr(route, "methods", set())
    ]
    if len(matches) != 1:
        raise CityOpsContractError("internal/admin matrix route registration drift")
    return matches[0]


def _assert_claims_adjacent_and_conservative(card: dict[str, Any]) -> None:
    boundaries = card.get("claim_boundaries", {})
    safe_to_claim = boundaries.get("safe_to_claim")
    do_not_claim_yet = boundaries.get("do_not_claim_yet")
    if not isinstance(safe_to_claim, list) or not isinstance(do_not_claim_yet, list):
        raise CityOpsContractError("internal/admin matrix route requires claim boundaries")
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(
            f"internal/admin matrix route refuses claim overlap: {overlap}"
        )

    claim_cards = card.get("claim_cards")
    if not isinstance(claim_cards, list) or [
        claim.get("card") for claim in claim_cards
    ] != ["safe_to_claim", "do_not_claim_yet"]:
        raise CityOpsContractError(
            "internal/admin matrix route requires adjacent safe/blocked claim cards"
        )
    if claim_cards[0].get("values") != safe_to_claim:
        raise CityOpsContractError("internal/admin matrix route safe claim card drift")
    if claim_cards[1].get("values") != do_not_claim_yet:
        raise CityOpsContractError("internal/admin matrix route blocked claim card drift")
