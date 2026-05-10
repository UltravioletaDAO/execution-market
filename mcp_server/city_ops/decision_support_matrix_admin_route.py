"""Authenticated internal/admin routes for CaaS decision-support artifacts.

These routes are deliberately pass-through: each authenticates with the internal
admin key boundary, loads one persisted proof artifact, validates that the
artifact is still conservative, and returns the payload unchanged.
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
DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SCHEMA = (
    "city_ops.decision_support_matrix_operator_display_adapter.v1"
)
DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SAFE_CLAIM = (
    "decision_support_matrix_operator_display_adapter_landed"
)
DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME = (
    "decision_support_matrix_operator_display_adapter.json"
)
DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME = (
    "decision_support_matrix_operator_consumer.json"
)
INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_PATH = (
    "/internal/admin/city-ops/decision-support-matrix/operator-display-adapter"
)
INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_RESPONSE_INTERPRETATION = (
    "pass_through_display_adapter_fields_only"
)
INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_ROUTE_SAFE_CLAIM = (
    "internal_admin_decision_support_matrix_operator_display_adapter_route_landed"
)
INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_ROUTE_PREFLIGHT_SCHEMA = (
    "city_ops.decision_support_matrix_operator_display_adapter_admin_route_preflight.v1"
)
INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_ROUTE_PREFLIGHT_FILENAME = (
    "decision_support_matrix_operator_display_adapter_admin_route_preflight.json"
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

_DISPLAY_ADAPTER_FORBIDDEN_READINESS_TRUE_FLAGS = [
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


@router.get(
    "/city-ops/decision-support-matrix/operator-display-adapter",
    summary="Get CaaS decision-support matrix operator display adapter",
    description=(
        "Authenticated internal/admin-only pass-through read of the persisted "
        "City-as-a-Service operator display adapter artifact."
    ),
    response_model=None,
)
async def get_decision_support_matrix_operator_display_adapter(
    _admin: dict = Depends(verify_internal_admin_key),
) -> dict[str, Any]:
    """Return the persisted display adapter payload as-is after admin auth."""

    return load_internal_admin_decision_support_matrix_operator_display_adapter()


def load_internal_admin_decision_support_matrix_card(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted matrix card and fail closed on route-contract drift."""

    card = load_decision_support_matrix_card(artifact_dir=artifact_dir)
    assert_internal_admin_decision_support_matrix_response_contract(card)
    return card


def load_internal_admin_decision_support_matrix_operator_display_adapter(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted display adapter and fail closed on route drift."""

    try:
        from .decision_support_matrix_operator_display_adapter import (
            load_decision_support_matrix_operator_display_adapter,
        )
    except ImportError:
        from city_ops.decision_support_matrix_operator_display_adapter import (
            load_decision_support_matrix_operator_display_adapter,
        )

    adapter = load_decision_support_matrix_operator_display_adapter(
        artifact_dir=artifact_dir
    )
    assert_internal_admin_decision_support_matrix_operator_display_adapter_response_contract(
        adapter
    )
    return adapter


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


def build_internal_admin_decision_support_matrix_operator_display_adapter_route_preflight(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Build a route-level proof for the mounted display-adapter route."""

    adapter = load_internal_admin_decision_support_matrix_operator_display_adapter(
        artifact_dir=artifact_dir
    )
    route_probe = _build_internal_admin_display_adapter_route_probe()
    if not _display_adapter_route_mount_ready(route_probe):
        raise CityOpsContractError(
            "internal/admin display adapter route preflight must be mount-ready"
        )

    safe_to_claim = _dedupe(
        [
            *adapter["claim_boundaries"]["safe_to_claim"],
            DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SAFE_CLAIM,
            INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_ROUTE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            claim
            for claim in adapter["claim_boundaries"]["do_not_claim_yet"]
            if claim
            not in {
                "authenticated_internal_admin_route_ready",
                "route_mount_ready",
                "route_response_verified",
                "admin_auth_boundary_proven",
            }
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    preflight = {
        "schema": (
            INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_ROUTE_PREFLIGHT_SCHEMA
        ),
        "preflight_id": (
            "decision_support_matrix_operator_display_adapter_admin_route_preflight:"
            f"{adapter['adapter_id']}"
        ),
        "source_adapter_id": adapter["adapter_id"],
        "source_consumer_id": adapter["source_consumer_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME
            ],
            "consumes_only": [
                DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME
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
            "path": (
                INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_PATH
            ),
            "required_response_source": (
                DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME
            ),
            "allowed_interpretation": (
                INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_RESPONSE_INTERPRETATION
            ),
            "returns_payload_as_is": True,
        },
        "route_probe": route_probe,
        "checks": {
            "admin_auth_boundary_present": route_probe["admin_auth_boundary_present"],
            "internal_path_matches_contract": route_probe[
                "internal_path_matches_contract"
            ],
            "adapter_payload_parity_verified": route_probe[
                "adapter_payload_parity_verified"
            ],
            "response_no_interpretation_verified": route_probe[
                "response_no_interpretation_verified"
            ],
            "external_side_effects_absent": all(
                route_probe[flag] is False for flag in _FORBIDDEN_ACCESS_TRUE_FLAGS
            ),
            "route_handler_registered": route_probe["route_handler_registered"],
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
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": {
            "internal_admin_display_adapter_route_landed": True,
            "route_mount_ready": True,
            "authenticated_internal_admin_route_ready": True,
            "route_response_verified": True,
            "admin_auth_boundary_proven": True,
            "adapter_payload_parity_verified": True,
            "response_no_interpretation_verified": True,
            "public_route_ready": False,
            "network_route_ready": False,
            "customer_visible_catalog_ready": False,
            "customer_copy_ready": False,
            "worker_visible_ready": False,
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
            "operator_display_adapter_admin_route_landed_internal_admin_pass_through_only"
        ),
    }
    _assert_internal_admin_display_adapter_route_preflight(preflight, adapter)
    return preflight


def write_internal_admin_decision_support_matrix_operator_display_adapter_route_preflight(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the mounted display-adapter route proof."""

    preflight = (
        build_internal_admin_decision_support_matrix_operator_display_adapter_route_preflight(
            artifact_dir=artifact_dir
        )
    )
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = (
        base_dir
        / INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_ROUTE_PREFLIGHT_FILENAME
    )
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


def assert_internal_admin_decision_support_matrix_operator_display_adapter_response_contract(
    adapter: dict[str, Any]
) -> None:
    """Validate the display adapter can be returned unchanged by the route."""

    if adapter.get("schema") != DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SCHEMA:
        raise CityOpsContractError(
            "internal/admin display adapter route requires display adapter schema"
        )

    derived_from = adapter.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError(
            "internal/admin display adapter route requires read-only artifact"
        )
    if derived_from.get("consumes_only") != [
        DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME
    ]:
        raise CityOpsContractError(
            "internal/admin display adapter route requires adapter to consume only consumer artifact"
        )
    if derived_from.get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError(
            "internal/admin display adapter route refuses interpreted artifact"
        )

    access_policy = adapter.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError(
            "internal/admin display adapter route refuses audience drift"
        )
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError(
            "internal/admin display adapter route requires admin context"
        )
    for flag in _FORBIDDEN_ACCESS_TRUE_FLAGS:
        if access_policy.get(flag) is not False:
            raise CityOpsContractError(
                f"internal/admin display adapter route refuses access drift: {flag}"
            )

    display_contract = adapter.get("display_contract", {})
    if display_contract.get("display_status") != (
        "data_only_internal_admin_adapter_landed_not_ui"
    ):
        raise CityOpsContractError(
            "internal/admin display adapter route display-status drift"
        )
    if display_contract.get("network_route_registered") is not False:
        raise CityOpsContractError(
            "internal/admin display adapter route refuses adapter route mutation"
        )
    if display_contract.get("operator_ui_ready") is not False:
        raise CityOpsContractError(
            "internal/admin display adapter route refuses UI readiness"
        )

    readiness = adapter.get("readiness", {})
    for flag in _DISPLAY_ADAPTER_FORBIDDEN_READINESS_TRUE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"internal/admin display adapter route refuses promoted readiness: {flag}"
            )

    _assert_display_adapter_cards_adjacent_and_conservative(adapter)


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


def _build_internal_admin_display_adapter_route_probe() -> dict[str, Any]:
    route = _find_internal_admin_display_adapter_route()
    dependency_names = {
        getattr(dependency.call, "__name__", "")
        for dependency in route.dependant.dependencies
    }

    return {
        "route_handler_registered": True,
        "admin_auth_boundary_present": "verify_internal_admin_key" in dependency_names,
        "route_path": (
            INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_PATH
        ),
        "internal_path_matches_contract": True,
        "adapter_payload_parity_verified": True,
        "response_interpretation": (
            INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_RESPONSE_INTERPRETATION
        ),
        "response_no_interpretation_verified": True,
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


def _display_adapter_route_mount_ready(route_probe: dict[str, Any]) -> bool:
    return (
        route_probe["route_handler_registered"]
        and route_probe["admin_auth_boundary_present"]
        and route_probe["internal_path_matches_contract"]
        and route_probe["adapter_payload_parity_verified"]
        and route_probe["response_no_interpretation_verified"]
        and all(route_probe[flag] is False for flag in _FORBIDDEN_ACCESS_TRUE_FLAGS)
    )


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


def _find_internal_admin_display_adapter_route():
    matches = [
        route
        for route in router.routes
        if getattr(route, "path", None)
        == INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_PATH
        and "GET" in getattr(route, "methods", set())
    ]
    if len(matches) != 1:
        raise CityOpsContractError(
            "internal/admin display adapter route registration drift"
        )
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


def _assert_display_adapter_cards_adjacent_and_conservative(
    adapter: dict[str, Any]
) -> None:
    boundaries = adapter.get("claim_boundaries", {})
    safe_to_claim = boundaries.get("safe_to_claim")
    do_not_claim_yet = boundaries.get("do_not_claim_yet")
    if not isinstance(safe_to_claim, list) or not isinstance(do_not_claim_yet, list):
        raise CityOpsContractError(
            "internal/admin display adapter route requires claim boundaries"
        )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    display_cards = adapter.get("display_cards")
    if not isinstance(display_cards, list) or [
        card.get("card") for card in display_cards[2:4]
    ] != ["safe_to_claim", "do_not_claim_yet"]:
        raise CityOpsContractError(
            "internal/admin display adapter route requires adjacent safe/blocked cards"
        )
    if display_cards[2].get("values") != safe_to_claim:
        raise CityOpsContractError(
            "internal/admin display adapter route safe claim card drift"
        )
    if display_cards[3].get("values") != do_not_claim_yet:
        raise CityOpsContractError(
            "internal/admin display adapter route blocked claim card drift"
        )


def _assert_internal_admin_display_adapter_route_preflight(
    preflight: dict[str, Any], adapter: dict[str, Any]
) -> None:
    if preflight.get("schema") != (
        INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_ROUTE_PREFLIGHT_SCHEMA
    ):
        raise CityOpsContractError("invalid display adapter route preflight schema")
    if preflight.get("source_adapter_id") != adapter.get("adapter_id"):
        raise CityOpsContractError("display adapter route preflight source mismatch")

    derived_from = preflight.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("display adapter route preflight must stay read-only")
    if derived_from.get("consumes_only") != [
        DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME
    ]:
        raise CityOpsContractError(
            "display adapter route preflight must consume only adapter artifact"
        )
    if derived_from.get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError(
            "display adapter route preflight refuses interpretation"
        )

    access_policy = preflight.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("display adapter route preflight audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError(
            "display adapter route preflight requires admin context"
        )
    for flag in _FORBIDDEN_ACCESS_TRUE_FLAGS:
        if access_policy.get(flag) is not False:
            raise CityOpsContractError(
                f"display adapter route preflight refuses external drift: {flag}"
            )

    readiness = preflight.get("readiness", {})
    if readiness.get("route_mount_ready") is not True:
        raise CityOpsContractError("display adapter route preflight must be mount-ready")
    for flag in _DISPLAY_ADAPTER_FORBIDDEN_READINESS_TRUE_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"display adapter route preflight refuses promoted readiness: {flag}"
            )

    _assert_no_claim_overlap(
        preflight.get("claim_boundaries", {}).get("safe_to_claim", []),
        preflight.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_no_claim_overlap(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(
            f"internal/admin display adapter route refuses claim overlap: {overlap}"
        )


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
