"""Internal/admin route mount proof for the AAS claim quarantine surface.

This module mounts exactly one authenticated internal/admin pass-through route for
``aas_claim_quarantine_read_surface.json`` and produces a conservative route
mount manifest. It does not create customer copy, delivery, publication,
public/catalog routes, pricing, pilots, queue launch, dispatch, ERC-8004
reputation, worker Skill DNA, live Acontext/runtime parity, payment or
production reverification, GPS/raw metadata release, domain authority, or
worker-copyable doctrine.
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
    from .aas_claim_quarantine_read_surface import (
        AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME,
        AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
        AAS_CLAIM_QUARANTINE_READ_SURFACE_SCHEMA,
        ACCESS_FALSE_FLAGS,
        READ_SURFACE_BLOCKED_CLAIMS,
        READINESS_FALSE_FLAGS,
        SURFACE_FALSE_FLAGS,
        SURFACE_STATUS,
        load_aas_claim_quarantine_read_surface,
    )
    from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
    from .contracts import CityOpsContractError
except ImportError:
    from city_ops.aas_claim_quarantine_read_surface import (
        AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME,
        AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
        AAS_CLAIM_QUARANTINE_READ_SURFACE_SCHEMA,
        ACCESS_FALSE_FLAGS,
        READ_SURFACE_BLOCKED_CLAIMS,
        READINESS_FALSE_FLAGS,
        SURFACE_FALSE_FLAGS,
        SURFACE_STATUS,
        load_aas_claim_quarantine_read_surface,
    )
    from city_ops.compliance_desk_fixture_review_gate import ARTIFACT_DIR
    from city_ops.contracts import CityOpsContractError

INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PATH = (
    "/internal/admin/city-ops/aas-claim-quarantine"
)
INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_RESPONSE_INTERPRETATION = (
    "pass_through_claim_quarantine_read_surface_fields_only"
)
INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SCHEMA = (
    "city_ops.aas_claim_quarantine_route_mount_manifest.v1"
)
INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SAFE_CLAIM = (
    "internal_admin_aas_claim_quarantine_route_mount_smoke_landed"
)
INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME = (
    "aas_claim_quarantine_route_mount_manifest.json"
)

ROUTE_MOUNT_BLOCKED_CLAIMS = [
    "claim_quarantine_route_is_public_or_customer_route",
    "claim_quarantine_route_authorizes_customer_delivery_or_publication",
    "claim_quarantine_route_approves_public_price_or_quote",
    "claim_quarantine_route_authorizes_pilot_or_queue_launch",
    "claim_quarantine_route_authorizes_dispatch",
    "claim_quarantine_route_emits_erc8004_reputation",
    "claim_quarantine_route_proves_worker_skill_dna",
    "claim_quarantine_route_proves_live_acontext_or_runtime_parity",
    "claim_quarantine_route_reverifies_payment_or_production",
    "claim_quarantine_route_allows_exact_gps_or_raw_metadata",
    "claim_quarantine_route_grants_domain_or_legal_authority",
    "claim_quarantine_route_creates_worker_copyable_doctrine",
]

ROUTE_FALSE_READINESS_FLAGS = {
    "app_level_router_include_smoke_passed": True,
    "expected_route_registered": True,
    "admin_auth_boundary_proven": True,
    "pass_through_response_semantics_preserved": True,
    "public_route_ready": False,
    "network_route_ready": False,
    "customer_visible_catalog_ready": False,
    "customer_copy_ready": False,
    "customer_delivery_ready": False,
    "publication_ready": False,
    "worker_visible_ready": False,
    "polished_operator_console_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_routing_ready": False,
    "dispatch_automation_ready": False,
    "live_acontext_ready": False,
    "acontext_sink_ready": False,
    "runtime_parity_proven": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "payment_or_production_reverified": False,
    "legal_or_regulator_ready": False,
    "gps_or_metadata_exposure_allowed": False,
    "worker_copyable_municipal_doctrine_ready": False,
}

ROUTE_FALSE_ACCESS_FLAGS = {
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "writes_municipal_memory": False,
    "emits_reputation_receipts": False,
    "exposes_gps_or_metadata": False,
    "publishes_worker_doctrine": False,
}

router = APIRouter(prefix="/internal/admin", tags=["Internal Admin"])


@router.get(
    "/city-ops/aas-claim-quarantine",
    summary="Get AAS claim quarantine read surface",
    description=(
        "Authenticated internal/admin-only pass-through read of the persisted "
        "AAS claim quarantine read surface."
    ),
    response_model=None,
)
async def get_aas_claim_quarantine_read_surface(
    _admin: dict = Depends(verify_internal_admin_key),
) -> dict[str, Any]:
    """Return the persisted quarantine surface as-is after admin auth and guards."""

    return load_internal_admin_aas_claim_quarantine_read_surface()


def load_internal_admin_aas_claim_quarantine_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted quarantine surface and fail closed on route drift."""

    surface = load_aas_claim_quarantine_read_surface(
        artifact_dir=Path(artifact_dir) if artifact_dir else None
    )
    assert_internal_admin_aas_claim_quarantine_response_contract(surface)
    return surface


def build_internal_admin_aas_claim_quarantine_route_mount_manifest(
    *, app_routes: list[Any] | None = None
) -> dict[str, Any]:
    """Prove the claim quarantine route mounts without broadening claims."""

    if app_routes is None:
        app = FastAPI()
        app.include_router(router)
        app_routes = list(app.routes)

    mounted_route = _summarize_mounted_internal_admin_route(app_routes)
    safe_to_claim = _dedupe(
        [
            AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
            INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *READ_SURFACE_BLOCKED_CLAIMS,
            *ROUTE_MOUNT_BLOCKED_CLAIMS,
        ]
    )

    manifest = {
        "schema": INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SCHEMA,
        "manifest_id": "aas_claim_quarantine_route_mount_manifest:internal_admin:v1",
        "derived_from": {
            "read_only": True,
            "source_router": "city_ops.aas_claim_quarantine_admin_route.router",
            "source_artifacts": [AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME],
            "consumes_only": [AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME],
            "semantic_reinterpretation_performed": False,
            "writes_customer_copy": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "writes_municipal_memory": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "publishes_worker_doctrine": False,
            "exposes_gps_or_metadata": False,
        },
        "mount_contract": {
            "mount_scope": "fastapi_app_include_router_smoke",
            "expected_route_count": 1,
            "mounted_route_count": 1,
            "allowed_methods": ["GET"],
            "required_prefix": "/internal/admin/",
            "required_dependency": "verify_internal_admin_key",
            "response_semantics": "pass_through_persisted_artifact_only",
        },
        "mounted_routes": [mounted_route],
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **ROUTE_FALSE_ACCESS_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": dict(ROUTE_FALSE_READINESS_FLAGS),
        "manifest_verdict": (
            "internal_admin_aas_claim_quarantine_route_mounts_without_external_claims"
        ),
    }
    _assert_internal_admin_aas_claim_quarantine_route_mount_manifest(manifest)
    return manifest


def write_internal_admin_aas_claim_quarantine_route_mount_manifest(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the claim quarantine route mount manifest."""

    manifest = build_internal_admin_aas_claim_quarantine_route_mount_manifest()
    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def assert_internal_admin_aas_claim_quarantine_response_contract(
    surface: dict[str, Any]
) -> None:
    """Validate the surface can be returned without reinterpretation."""

    if surface.get("schema") != AAS_CLAIM_QUARANTINE_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("claim quarantine route requires read surface schema")
    if surface.get("surface_status") != SURFACE_STATUS:
        raise CityOpsContractError("claim quarantine route source status drift")

    render = surface.get("render_contract", {})
    if render.get("allowed_interpretation") != "pass_through_quarantine_board_fields_only":
        raise CityOpsContractError("claim quarantine route requires pass-through semantics")
    if render.get("suggested_internal_path") != INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PATH:
        raise CityOpsContractError("claim quarantine route path drift")
    for flag in ["network_route_registered", "public_route_registered"]:
        if render.get(flag) is not False:
            raise CityOpsContractError(f"claim quarantine route render promoted {flag}")

    safe_to_claim = surface.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim_yet = surface.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("claim quarantine route safe claim missing")
    if set(safe_to_claim) & set(do_not_claim_yet):
        raise CityOpsContractError("claim quarantine route safe/blocked overlap")
    missing_blocked = set(READ_SURFACE_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"claim quarantine route missing blocked claims: {sorted(missing_blocked)}"
        )

    for flag, expected in ACCESS_FALSE_FLAGS.items():
        if surface.get("access_policy", {}).get(flag) is not expected:
            raise CityOpsContractError(f"claim quarantine route source promoted access {flag}")
    for flag, expected in READINESS_FALSE_FLAGS.items():
        if surface.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"claim quarantine route source promoted readiness {flag}")
    for flag, expected in SURFACE_FALSE_FLAGS.items():
        if surface.get(flag) is not expected:
            raise CityOpsContractError(f"claim quarantine route source promoted {flag}")


def _summarize_mounted_internal_admin_route(app_routes: list[Any]) -> dict[str, Any]:
    matches = [
        route
        for route in app_routes
        if getattr(route, "path", None) == INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PATH
    ]
    if len(matches) != 1:
        raise CityOpsContractError("claim quarantine route mount count drift")

    route = matches[0]
    methods = sorted(getattr(route, "methods", set()) or [])
    if methods != ["GET"]:
        raise CityOpsContractError("claim quarantine route method drift")

    dependency_names = sorted(
        getattr(dep.call, "__name__", "")
        for dep in getattr(getattr(route, "dependant", None), "dependencies", [])
    )
    if "verify_internal_admin_key" not in dependency_names:
        raise CityOpsContractError("claim quarantine route admin auth dependency missing")

    return {
        "route_key": "aas_claim_quarantine_read_surface",
        "path": INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PATH,
        "methods": methods,
        "handler": getattr(getattr(route, "endpoint", None), "__name__", ""),
        "dependency_names": dependency_names,
        "response_source": AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME,
        "response_schema": AAS_CLAIM_QUARANTINE_READ_SURFACE_SCHEMA,
        "allowed_interpretation": (
            INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_RESPONSE_INTERPRETATION
        ),
        "public_or_customer_visible": False,
        "writes_live_acontext": False,
        "dispatch_enabled": False,
        "emits_reputation_receipts": False,
    }


def _assert_internal_admin_aas_claim_quarantine_route_mount_manifest(
    manifest: dict[str, Any]
) -> None:
    if manifest.get("schema") != INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SCHEMA:
        raise CityOpsContractError("claim quarantine route mount manifest schema drift")
    if manifest.get("mount_contract", {}).get("mounted_route_count") != 1:
        raise CityOpsContractError("claim quarantine route-count drift")
    if len(manifest.get("mounted_routes", [])) != 1:
        raise CityOpsContractError("claim quarantine mounted routes drift")
    mounted = manifest["mounted_routes"][0]
    if mounted.get("path") != INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PATH:
        raise CityOpsContractError("claim quarantine mounted path drift")
    if mounted.get("methods") != ["GET"]:
        raise CityOpsContractError("claim quarantine mounted method drift")
    if "verify_internal_admin_key" not in mounted.get("dependency_names", []):
        raise CityOpsContractError("claim quarantine mounted admin auth missing")

    safe_to_claim = manifest.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim_yet = manifest.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("claim quarantine mount manifest safe claim missing")
    if set(safe_to_claim) & set(do_not_claim_yet):
        raise CityOpsContractError("claim quarantine mount manifest claim overlap")
    missing_blocked = set(ROUTE_MOUNT_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"claim quarantine mount manifest missing blocked claims: {sorted(missing_blocked)}"
        )

    for flag, expected in ROUTE_FALSE_ACCESS_FLAGS.items():
        if manifest.get("access_policy", {}).get(flag) is not expected:
            raise CityOpsContractError(f"claim quarantine mount promoted access {flag}")
    for flag, expected in ROUTE_FALSE_READINESS_FLAGS.items():
        if manifest.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"claim quarantine mount promoted readiness {flag}")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
