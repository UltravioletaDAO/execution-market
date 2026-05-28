"""Internal/admin route proof for the AAS system-integration flywheel surface.

This module mounts one authenticated internal/admin pass-through route for the
persisted system-integration flywheel read surface and emits a conservative
preflight artifact for that mount. It does not create customer copy, public or
catalog routes, dispatch, ERC-8004 reputation, live Acontext/runtime parity,
payment or production reverification, GPS/raw metadata exposure, legal/notarial/
custody/emergency/safety/repair/insurance/SLA/official-report/fault-liability
authority, or worker-copyable doctrine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, FastAPI

try:  # Package imports used by tests from the repository root.
    from mcp_server.admin_auth import verify_internal_admin_key
except ImportError:  # Runtime server imports modules from mcp_server/ as top-level packages.
    from admin_auth import verify_internal_admin_key

try:
    from .aas_system_integration_flywheel_read_surface import (
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME,
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM,
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SCHEMA,
        SURFACE_BLOCKED_CLAIMS,
        _FALSE_ACCESS_FLAGS,
        _FALSE_DERIVED_FLAGS,
        _FALSE_READINESS_FLAGS,
        load_aas_system_integration_flywheel_read_surface,
    )
    from .aas_system_integration_flywheel import FLYWHEEL_BLOCKED_CLAIMS
    from .contracts import CityOpsContractError
    from .proof_block_artifacts import _default_proof_block_dir
except ImportError:
    from city_ops.aas_system_integration_flywheel_read_surface import (
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME,
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM,
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SCHEMA,
        SURFACE_BLOCKED_CLAIMS,
        _FALSE_ACCESS_FLAGS,
        _FALSE_DERIVED_FLAGS,
        _FALSE_READINESS_FLAGS,
        load_aas_system_integration_flywheel_read_surface,
    )
    from city_ops.aas_system_integration_flywheel import FLYWHEEL_BLOCKED_CLAIMS
    from city_ops.contracts import CityOpsContractError
    from city_ops.proof_block_artifacts import _default_proof_block_dir

INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH = (
    "/internal/admin/city-ops/aas-system-integration-flywheel"
)
INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_RESPONSE_INTERPRETATION = (
    "pass_through_flywheel_fields_only"
)
INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SCHEMA = (
    "city_ops.aas_system_integration_flywheel_admin_route_preflight.v1"
)
INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SAFE_CLAIM = (
    "internal_admin_aas_system_integration_flywheel_route_preflight_landed"
)
INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME = (
    "aas_system_integration_flywheel_admin_route_preflight.json"
)

ROUTE_BLOCKED_CLAIMS = [
    *FLYWHEEL_BLOCKED_CLAIMS,
    *SURFACE_BLOCKED_CLAIMS,
    "system_integration_flywheel_route_is_public_or_customer_route",
    "system_integration_flywheel_route_authorizes_customer_delivery_or_publication",
    "system_integration_flywheel_route_registers_catalog_or_public_route",
    "system_integration_flywheel_route_authorizes_dispatch_or_worker_visibility",
    "system_integration_flywheel_route_emits_erc8004_reputation",
    "system_integration_flywheel_route_proves_live_acontext_or_runtime_parity",
    "system_integration_flywheel_route_reverifies_payment_or_production",
    "system_integration_flywheel_route_allows_exact_gps_or_raw_metadata",
    "system_integration_flywheel_route_grants_legal_regulator_notarial_or_custody_authority",
    "system_integration_flywheel_route_grants_emergency_safety_repair_insurance_sla_official_report_or_fault_liability_authority",
    "system_integration_flywheel_route_creates_worker_copyable_doctrine",
]

ROUTE_FALSE_ACCESS_FLAGS = {
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

ROUTE_READINESS_FLAGS = {
    "route_preflight_landed": True,
    "app_level_router_include_smoke_passed": True,
    "expected_route_registered": True,
    "admin_auth_boundary_proven": True,
    "pass_through_response_semantics_preserved": True,
    "persisted_surface_payload_verified": True,
    "public_route_ready": False,
    "network_route_ready": False,
    "customer_visible_catalog_ready": False,
    "customer_copy_ready": False,
    "customer_delivery_ready": False,
    "publication_ready": False,
    "worker_visible_ready": False,
    "dispatch_routing_ready": False,
    "dispatch_automation_ready": False,
    "live_acontext_ready": False,
    "acontext_sink_ready": False,
    "runtime_parity_proven": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "payment_or_production_reverified": False,
    "legal_or_regulator_ready": False,
    "notarial_or_custody_ready": False,
    "emergency_safety_repair_insurance_sla_official_report_or_fault_liability_ready": False,
    "gps_or_metadata_exposure_allowed": False,
    "worker_copyable_municipal_doctrine_ready": False,
}

router = APIRouter(prefix="/internal/admin", tags=["Internal Admin"])


@router.get(
    "/city-ops/aas-system-integration-flywheel",
    summary="Get AAS system-integration flywheel read surface",
    description=(
        "Authenticated internal/admin-only pass-through read of the persisted "
        "City-as-a-Service AAS system-integration flywheel read surface."
    ),
    response_model=None,
)
async def get_aas_system_integration_flywheel_read_surface(
    _admin: dict = Depends(verify_internal_admin_key),
) -> dict[str, Any]:
    """Return the persisted flywheel read surface unchanged after admin auth."""

    return load_internal_admin_aas_system_integration_flywheel_read_surface()


def load_internal_admin_aas_system_integration_flywheel_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted surface and fail closed on route-contract drift."""

    surface = load_aas_system_integration_flywheel_read_surface(
        artifact_dir=artifact_dir
    )
    assert_internal_admin_aas_system_integration_flywheel_response_contract(surface)
    return surface


def build_internal_admin_aas_system_integration_flywheel_route_preflight(
    *,
    artifact_dir: str | Path | None = None,
    app_routes: list[Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative preflight proof for the mounted internal/admin route."""

    surface = load_internal_admin_aas_system_integration_flywheel_read_surface(
        artifact_dir=artifact_dir
    )
    if app_routes is None:
        app = FastAPI()
        app.include_router(router)
        app_routes = list(app.routes)

    mounted_routes = [
        _summarize_mounted_route(app_routes),
    ]
    safe_to_claim = _dedupe(
        [
            *surface["claim_boundaries"]["safe_to_claim"],
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM,
            INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *surface["claim_boundaries"]["do_not_claim_yet"],
            *ROUTE_BLOCKED_CLAIMS,
        ]
    )

    preflight = {
        "schema": INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SCHEMA,
        "preflight_id": (
            "aas_system_integration_flywheel_admin_route_preflight:"
            f"{surface['surface_id']}"
        ),
        "source_surface_id": surface["surface_id"],
        "source_flywheel_id": surface["source_flywheel_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME],
            "consumes_only": [AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME],
            "semantic_reinterpretation_performed": False,
            "writes_customer_copy": False,
            "writes_live_acontext": False,
            "writes_municipal_memory": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "reverifies_payment_coverage": False,
            "reverifies_production_infrastructure": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "route_contract": {
            "method": "GET",
            "path": INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH,
            "required_response_source": AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME,
            "allowed_interpretation": (
                INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_RESPONSE_INTERPRETATION
            ),
            "returns_payload_as_is": True,
        },
        "mounted_routes": mounted_routes,
        "checks": {
            "app_level_router_include_smoke_passed": True,
            "expected_route_registered": len(mounted_routes) == 1,
            "admin_auth_boundary_present": mounted_routes[0][
                "admin_auth_boundary_present"
            ],
            "surface_payload_parity_verified": True,
            "response_no_interpretation_verified": True,
            "external_side_effects_absent": all(
                mounted_routes[0][flag] is False for flag in ROUTE_FALSE_ACCESS_FLAGS
            ),
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **ROUTE_FALSE_ACCESS_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": dict(ROUTE_READINESS_FLAGS),
        "preflight_verdict": (
            "system_integration_flywheel_admin_route_landed_internal_admin_pass_through_only"
        ),
    }
    _assert_internal_admin_aas_system_integration_flywheel_route_preflight(
        preflight, surface
    )
    return preflight


def write_internal_admin_aas_system_integration_flywheel_route_preflight(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the mounted route preflight proof."""

    preflight = build_internal_admin_aas_system_integration_flywheel_route_preflight(
        artifact_dir=artifact_dir
    )
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME
    path.write_text(json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def assert_internal_admin_aas_system_integration_flywheel_response_contract(
    surface: dict[str, Any]
) -> None:
    """Validate the surface can be returned unchanged by the admin route."""

    if surface.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("system integration flywheel route requires read surface schema")

    derived_from = surface.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("system integration flywheel route requires read-only surface")
    if derived_from.get("consumes_only") != ["aas_system_integration_flywheel.json"]:
        raise CityOpsContractError("system integration flywheel route source drift")
    for flag in _FALSE_DERIVED_FLAGS:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(
                f"system integration flywheel route refuses derived drift: {flag}"
            )

    access_policy = surface.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("system integration flywheel route refuses audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("system integration flywheel route requires admin context")
    for flag in _FALSE_ACCESS_FLAGS:
        if access_policy.get(flag) is not False:
            raise CityOpsContractError(
                f"system integration flywheel route refuses access drift: {flag}"
            )

    render_contract = surface.get("render_contract", {})
    if render_contract.get("suggested_internal_path") != (
        INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH
    ):
        raise CityOpsContractError("system integration flywheel route path drift")
    if render_contract.get("allowed_interpretation") != (
        INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_RESPONSE_INTERPRETATION
    ):
        raise CityOpsContractError("system integration flywheel route interpretation drift")
    if render_contract.get("network_route_registered") is not False:
        raise CityOpsContractError("system integration flywheel route refuses network route promotion")
    for field in render_contract.get("response_fields", []):
        if field not in surface:
            raise CityOpsContractError(
                f"system integration flywheel route missing pass-through field: {field}"
            )

    readiness = surface.get("readiness", {})
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"system integration flywheel route refuses promoted readiness: {flag}"
            )

    _assert_claim_boundaries(
        surface.get("claim_boundaries", {}).get("safe_to_claim", []),
        surface.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _summarize_mounted_route(app_routes: list[Any]) -> dict[str, Any]:
    matches = [
        route
        for route in app_routes
        if getattr(route, "path", None) == INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH
    ]
    if len(matches) != 1:
        raise CityOpsContractError("system integration flywheel route mount count drift")

    route = matches[0]
    methods = sorted(getattr(route, "methods", set()) or [])
    dependency_names = {
        getattr(dependency.call, "__name__", "")
        for dependency in getattr(route, "dependant", None).dependencies
    }
    if methods != ["GET"]:
        raise CityOpsContractError("system integration flywheel route refuses method drift")
    if not INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH.startswith(
        "/internal/admin/"
    ):
        raise CityOpsContractError("system integration flywheel route refuses public path")
    if "verify_internal_admin_key" not in dependency_names:
        raise CityOpsContractError("system integration flywheel route missing admin auth")

    return {
        "route_key": "aas_system_integration_flywheel_read_surface",
        "path": INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH,
        "methods": methods,
        "route_handler_registered": True,
        "admin_auth_boundary_present": True,
        "internal_path_matches_contract": True,
        "response_source": AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME,
        "allowed_interpretation": (
            INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_RESPONSE_INTERPRETATION
        ),
        "returns_payload_as_is": True,
        **ROUTE_FALSE_ACCESS_FLAGS,
    }


def _assert_internal_admin_aas_system_integration_flywheel_route_preflight(
    preflight: dict[str, Any], surface: dict[str, Any]
) -> None:
    if preflight.get("schema") != (
        INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SCHEMA
    ):
        raise CityOpsContractError("invalid system integration flywheel route preflight schema")
    if preflight.get("source_surface_id") != surface.get("surface_id"):
        raise CityOpsContractError("system integration flywheel route preflight source drift")
    if preflight.get("route_contract", {}).get("path") != (
        INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH
    ):
        raise CityOpsContractError("system integration flywheel route preflight path drift")
    if preflight.get("route_contract", {}).get("returns_payload_as_is") is not True:
        raise CityOpsContractError("system integration flywheel route must pass through payload")
    mounted = preflight.get("mounted_routes", [])
    if len(mounted) != 1:
        raise CityOpsContractError("system integration flywheel route preflight mount count drift")
    for key, expected in ROUTE_FALSE_ACCESS_FLAGS.items():
        if preflight.get("access_policy", {}).get(key) is not expected:
            raise CityOpsContractError(f"system integration flywheel route access drift: {key}")
        if mounted[0].get(key) is not expected:
            raise CityOpsContractError(f"system integration flywheel mounted route drift: {key}")
    for key, expected in ROUTE_READINESS_FLAGS.items():
        if preflight.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(
                f"system integration flywheel route readiness drift: {key}"
            )
    _assert_claim_boundaries(
        preflight.get("claim_boundaries", {}).get("safe_to_claim", []),
        preflight.get("claim_boundaries", {}).get("do_not_claim_yet", []),
        require_route_claim=True,
    )


def _assert_claim_boundaries(
    safe_to_claim: list[str],
    do_not_claim_yet: list[str],
    *,
    require_route_claim: bool = False,
) -> None:
    blocked = set(ROUTE_BLOCKED_CLAIMS)
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(
            f"system integration flywheel route claim boundary overlap: {overlap}"
        )
    blocked_safe = sorted(set(safe_to_claim) & blocked)
    if blocked_safe:
        raise CityOpsContractError(
            f"system integration flywheel route blocked claims marked safe: {blocked_safe}"
        )
    missing = blocked - set(do_not_claim_yet)
    if require_route_claim and INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("system integration flywheel route missing safe claim")
    if missing and require_route_claim:
        raise CityOpsContractError(
            f"system integration flywheel route missing blocked claims: {sorted(missing)}"
        )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
