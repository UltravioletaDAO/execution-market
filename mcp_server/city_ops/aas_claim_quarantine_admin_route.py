"""Internal/admin route mount proofs for AAS claim quarantine surfaces.

This module mounts authenticated internal/admin pass-through routes for the
persisted claim-quarantine read artifacts and produces conservative route
mount/preflight artifacts. It does not create customer copy, delivery,
publication, public/catalog routes, pricing, pilots, queue launch, dispatch,
ERC-8004 reputation, worker Skill DNA, live Acontext/runtime parity, payment or
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
INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH = (
    "/internal/admin/city-ops/aas-claim-quarantine/prevented-claim-trends"
)
INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_RESPONSE_INTERPRETATION = (
    "pass_through_claim_quarantine_read_surface_fields_only"
)
INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_RESPONSE_INTERPRETATION = (
    "pass_through_prevented_claim_trend_read_surface_fields_only"
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
AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SCHEMA = (
    "city_ops.aas_claim_quarantine_prevented_claim_trend_read_surface.v1"
)
AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME = (
    "aas_claim_quarantine_prevented_claim_trend_read_surface.json"
)
AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM = (
    "internal_admin_aas_claim_quarantine_prevented_claim_trend_read_surface_landed"
)
TREND_READ_SURFACE_SCOPE = "internal_admin_prevented_claim_trend_cards_only_no_route"
TREND_READ_SURFACE_VERDICT = "prevented_claim_trend_cards_ready_for_internal_review_only"
INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SCHEMA = (
    "city_ops.aas_claim_quarantine_prevented_claim_trend_route_preflight.v1"
)
INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SAFE_CLAIM = (
    "internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight_landed"
)
INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_FILENAME = (
    "aas_claim_quarantine_prevented_claim_trend_route_preflight.json"
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

TREND_READ_SURFACE_BLOCKED_CLAIMS = [
    "trend_read_surface_is_network_route",
    "trend_read_surface_is_human_approval_record",
    "trend_read_surface_approves_customer_copy",
    "trend_read_surface_authorizes_customer_delivery",
    "trend_read_surface_authorizes_publication",
    "trend_read_surface_registers_public_or_catalog_route",
    "trend_read_surface_approves_public_price_or_quote",
    "trend_read_surface_authorizes_controlled_pilot_or_queue_launch",
    "trend_read_surface_authorizes_dispatch",
    "trend_read_surface_authorizes_erc8004_reputation",
    "trend_read_surface_proves_worker_skill_dna",
    "trend_read_surface_proves_live_acontext_or_runtime_parity",
    "trend_read_surface_reverifies_payment_or_production",
    "trend_read_surface_allows_exact_gps_or_raw_metadata",
    "trend_read_surface_grants_domain_legal_notarial_custody_or_incident_authority",
    "trend_read_surface_creates_worker_copyable_aas_doctrine",
]

TREND_READ_SURFACE_READINESS_FLAGS = {
    "trend_read_surface_landed": True,
    "source_trend_summary_verified": True,
    "operator_cards_ready": True,
    "connection_map_ready": True,
    "next_proof_slots_preserved": True,
    "network_route_registered": False,
    "customer_copy_ready": False,
    "customer_delivery_ready": False,
    "publication_ready": False,
    "public_or_catalog_route_ready": False,
    "pricing_or_customer_quote_ready": False,
    "controlled_pilot_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_ready": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "live_acontext_runtime_parity_ready": False,
    "payment_or_production_reverified": False,
    "exact_gps_or_raw_metadata_release_ready": False,
    "domain_authority_ready": False,
    "worker_copyable_doctrine_ready": False,
}

TREND_READ_SURFACE_FALSE_FLAGS = {
    "surface_is_network_route": False,
    "surface_is_human_approval_record": False,
    "surface_approves_customer_copy": False,
    "surface_authorizes_customer_delivery": False,
    "surface_authorizes_publication": False,
    "surface_registers_public_or_catalog_route": False,
    "surface_approves_public_price_or_quote": False,
    "surface_authorizes_controlled_pilot": False,
    "surface_authorizes_operator_queue_launch": False,
    "surface_authorizes_dispatch": False,
    "surface_emits_or_authorizes_reputation": False,
    "surface_proves_worker_skill_dna": False,
    "surface_proves_live_acontext_or_runtime_parity": False,
    "surface_reverifies_payment_or_production_health": False,
    "surface_allows_exact_gps_or_raw_metadata_release": False,
    "surface_grants_domain_legal_notarial_custody_or_incident_authority": False,
    "surface_creates_worker_copyable_aas_doctrine": False,
}

PREVENTED_CLAIM_TREND_ROUTE_BLOCKED_CLAIMS = [
    *TREND_READ_SURFACE_BLOCKED_CLAIMS,
    "prevented_claim_trend_route_is_public_or_customer_route",
    "prevented_claim_trend_route_authorizes_customer_delivery_or_publication",
    "prevented_claim_trend_route_approves_public_price_or_quote",
    "prevented_claim_trend_route_authorizes_pilot_or_queue_launch",
    "prevented_claim_trend_route_authorizes_dispatch",
    "prevented_claim_trend_route_emits_erc8004_reputation",
    "prevented_claim_trend_route_proves_worker_skill_dna",
    "prevented_claim_trend_route_proves_live_acontext_or_runtime_parity",
    "prevented_claim_trend_route_reverifies_payment_or_production",
    "prevented_claim_trend_route_allows_exact_gps_or_raw_metadata",
    "prevented_claim_trend_route_grants_domain_or_legal_authority",
    "prevented_claim_trend_route_creates_worker_copyable_doctrine",
]

PREVENTED_CLAIM_TREND_ROUTE_FALSE_READINESS_FLAGS = {
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


@router.get(
    "/city-ops/aas-claim-quarantine/prevented-claim-trends",
    summary="Get AAS claim quarantine prevented-claim trend cards",
    description=(
        "Authenticated internal/admin-only pass-through read of the persisted "
        "AAS claim quarantine prevented-claim trend read surface."
    ),
    response_model=None,
)
async def get_aas_claim_quarantine_prevented_claim_trend_read_surface(
    _admin: dict = Depends(verify_internal_admin_key),
) -> dict[str, Any]:
    """Return the persisted trend-card surface as-is after admin auth and guards."""

    return load_internal_admin_aas_claim_quarantine_prevented_claim_trend_read_surface()


def load_internal_admin_aas_claim_quarantine_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted quarantine surface and fail closed on route drift."""

    surface = load_aas_claim_quarantine_read_surface(
        artifact_dir=Path(artifact_dir) if artifact_dir else None
    )
    assert_internal_admin_aas_claim_quarantine_response_contract(surface)
    return surface


def load_internal_admin_aas_claim_quarantine_prevented_claim_trend_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted prevented-claim trend surface and fail closed on drift."""

    try:
        from .aas_claim_quarantine_prevented_claim_trend_read_surface import (
            load_aas_claim_quarantine_prevented_claim_trend_read_surface,
        )
    except ImportError:
        from city_ops.aas_claim_quarantine_prevented_claim_trend_read_surface import (
            load_aas_claim_quarantine_prevented_claim_trend_read_surface,
        )

    surface = load_aas_claim_quarantine_prevented_claim_trend_read_surface(
        artifact_dir=Path(artifact_dir) if artifact_dir else None
    )
    assert_internal_admin_aas_claim_quarantine_prevented_claim_trend_response_contract(
        surface
    )
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


def build_internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight(
    *, artifact_dir: str | Path | None = None, app_routes: list[Any] | None = None
) -> dict[str, Any]:
    """Prove the prevented-claim trend route is admin-only and pass-through."""

    surface = load_internal_admin_aas_claim_quarantine_prevented_claim_trend_read_surface(
        artifact_dir=artifact_dir
    )
    if app_routes is None:
        app = FastAPI()
        app.include_router(router)
        app_routes = list(app.routes)

    mounted_route = _summarize_mounted_internal_admin_prevented_claim_trend_route(
        app_routes
    )
    safe_to_claim = _dedupe(
        [
            *surface["claim_boundaries"]["safe_to_claim"],
            AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM,
            INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *surface["claim_boundaries"]["do_not_claim_yet"],
            *PREVENTED_CLAIM_TREND_ROUTE_BLOCKED_CLAIMS,
        ]
    )

    preflight = {
        "schema": (
            INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SCHEMA
        ),
        "preflight_id": (
            "aas_claim_quarantine_prevented_claim_trend_route_preflight:"
            "internal_admin:v1"
        ),
        "source_surface_id": surface["surface_id"],
        "source_artifact": {
            "file": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME,
            "schema": surface["schema"],
            "id": surface["surface_id"],
            "safe_claim": (
                AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM
            ),
        },
        "derived_from": {
            "read_only": True,
            "source_router": "city_ops.aas_claim_quarantine_admin_route.router",
            "source_artifacts": [
                AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME
            ],
            "consumes_only": [
                AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME
            ],
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
        "route_contract": {
            "method": "GET",
            "path": INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH,
            "required_response_source": (
                AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME
            ),
            "required_response_schema": (
                AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SCHEMA
            ),
            "allowed_interpretation": (
                INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_RESPONSE_INTERPRETATION
            ),
            "returns_payload_as_is": True,
            "route_registered_by_this_slice": True,
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
        "checks": {
            "admin_auth_boundary_present": True,
            "internal_path_matches_contract": True,
            "surface_payload_parity_verified": True,
            "response_no_interpretation_verified": True,
            "external_side_effects_absent": True,
            "route_handler_registered": True,
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
        "readiness": dict(PREVENTED_CLAIM_TREND_ROUTE_FALSE_READINESS_FLAGS),
        "preflight_verdict": (
            "internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight_mount_ready_pass_through_only"
        ),
        "next_smallest_proof": (
            "If operators need the trend cards in the admin app, keep this exact "
            "authenticated pass-through route. Any customer/public exposure still requires "
            "a separate human approval artifact naming exact copy, redactions, delivery path, "
            "and still-blocked claims."
        ),
    }
    _assert_internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight(
        preflight, surface
    )
    return preflight


def write_internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the prevented-claim trend route preflight fixture."""

    preflight = build_internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight(
        artifact_dir=artifact_dir
    )
    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    path = (
        base_dir
        / INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_FILENAME
    )
    path.write_text(json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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


def assert_internal_admin_aas_claim_quarantine_prevented_claim_trend_response_contract(
    surface: dict[str, Any]
) -> None:
    """Validate the trend-card surface can be returned without reinterpretation."""

    if surface.get("schema") != AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("prevented-claim trend route requires read surface schema")
    if surface.get("scope") != TREND_READ_SURFACE_SCOPE:
        raise CityOpsContractError("prevented-claim trend route source scope drift")
    if surface.get("surface_verdict") != TREND_READ_SURFACE_VERDICT:
        raise CityOpsContractError("prevented-claim trend route source verdict drift")

    derived_from = surface.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("prevented-claim trend route requires read-only source")
    if derived_from.get("adds_route") is not False:
        raise CityOpsContractError("prevented-claim trend route refuses source route drift")
    if derived_from.get("semantic_reinterpretation_performed") is not False:
        raise CityOpsContractError("prevented-claim trend route refuses source interpretation drift")

    safe_to_claim = surface.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim_yet = surface.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("prevented-claim trend route source safe claim missing")
    if set(safe_to_claim) & set(do_not_claim_yet):
        raise CityOpsContractError("prevented-claim trend route source safe/blocked overlap")
    missing_blocked = set(TREND_READ_SURFACE_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"prevented-claim trend route missing blocked claims: {sorted(missing_blocked)}"
        )

    access_policy = surface.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("prevented-claim trend route source audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("prevented-claim trend route source admin context drift")
    if access_policy.get("network_route_registered") is not False:
        raise CityOpsContractError("prevented-claim trend route source network route drift")

    for flag, expected in TREND_READ_SURFACE_READINESS_FLAGS.items():
        if surface.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"prevented-claim trend route source readiness drift: {flag}"
            )
    for flag, expected in TREND_READ_SURFACE_FALSE_FLAGS.items():
        if surface.get(flag) is not expected:
            raise CityOpsContractError(
                f"prevented-claim trend route source promoted flag: {flag}"
            )


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


def _summarize_mounted_internal_admin_prevented_claim_trend_route(
    app_routes: list[Any],
) -> dict[str, Any]:
    matches = [
        route
        for route in app_routes
        if getattr(route, "path", None)
        == INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH
    ]
    if len(matches) != 1:
        raise CityOpsContractError("prevented-claim trend route mount count drift")

    route = matches[0]
    methods = sorted(getattr(route, "methods", set()) or [])
    if methods != ["GET"]:
        raise CityOpsContractError("prevented-claim trend route method drift")

    dependency_names = sorted(
        getattr(dep.call, "__name__", "")
        for dep in getattr(getattr(route, "dependant", None), "dependencies", [])
    )
    if "verify_internal_admin_key" not in dependency_names:
        raise CityOpsContractError("prevented-claim trend route admin auth dependency missing")

    return {
        "route_key": "aas_claim_quarantine_prevented_claim_trend_read_surface",
        "path": INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH,
        "methods": methods,
        "handler": getattr(getattr(route, "endpoint", None), "__name__", ""),
        "dependency_names": dependency_names,
        "response_source": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME,
        "response_schema": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SCHEMA,
        "allowed_interpretation": (
            INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_RESPONSE_INTERPRETATION
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


def _assert_internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight(
    preflight: dict[str, Any], surface: dict[str, Any]
) -> None:
    if preflight.get("schema") != (
        INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SCHEMA
    ):
        raise CityOpsContractError("prevented-claim trend route preflight schema drift")
    if preflight.get("source_surface_id") != surface.get("surface_id"):
        raise CityOpsContractError("prevented-claim trend route preflight source drift")

    derived_from = preflight.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("prevented-claim trend route preflight must stay read-only")
    if derived_from.get("consumes_only") != [
        AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME
    ]:
        raise CityOpsContractError("prevented-claim trend route preflight consumes drift")
    for flag in [
        "semantic_reinterpretation_performed",
        "writes_customer_copy",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "writes_municipal_memory",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "publishes_worker_doctrine",
        "exposes_gps_or_metadata",
    ]:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(
                f"prevented-claim trend route preflight promoted derived flag: {flag}"
            )

    route_contract = preflight.get("route_contract", {})
    if route_contract.get("path") != INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH:
        raise CityOpsContractError("prevented-claim trend route preflight path drift")
    if route_contract.get("method") != "GET":
        raise CityOpsContractError("prevented-claim trend route preflight method drift")
    if route_contract.get("returns_payload_as_is") is not True:
        raise CityOpsContractError("prevented-claim trend route preflight must be pass-through")

    if preflight.get("mount_contract", {}).get("mounted_route_count") != 1:
        raise CityOpsContractError("prevented-claim trend route preflight route-count drift")
    if len(preflight.get("mounted_routes", [])) != 1:
        raise CityOpsContractError("prevented-claim trend route preflight mounted routes drift")
    mounted = preflight["mounted_routes"][0]
    if mounted.get("path") != INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH:
        raise CityOpsContractError("prevented-claim trend route preflight mounted path drift")
    if mounted.get("methods") != ["GET"]:
        raise CityOpsContractError("prevented-claim trend route preflight mounted method drift")
    if "verify_internal_admin_key" not in mounted.get("dependency_names", []):
        raise CityOpsContractError("prevented-claim trend route preflight admin auth missing")
    for flag in [
        "public_or_customer_visible",
        "writes_live_acontext",
        "dispatch_enabled",
        "emits_reputation_receipts",
    ]:
        if mounted.get(flag) is not False:
            raise CityOpsContractError(
                f"prevented-claim trend route preflight mounted route promoted {flag}"
            )

    checks = preflight.get("checks", {})
    for flag in [
        "admin_auth_boundary_present",
        "internal_path_matches_contract",
        "surface_payload_parity_verified",
        "response_no_interpretation_verified",
        "external_side_effects_absent",
        "route_handler_registered",
    ]:
        if checks.get(flag) is not True:
            raise CityOpsContractError(
                f"prevented-claim trend route preflight check failed: {flag}"
            )

    safe_to_claim = preflight.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim_yet = preflight.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if (
        INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SAFE_CLAIM
        not in safe_to_claim
    ):
        raise CityOpsContractError("prevented-claim trend route preflight safe claim missing")
    if set(safe_to_claim) & set(do_not_claim_yet):
        raise CityOpsContractError("prevented-claim trend route preflight claim overlap")
    missing_blocked = set(PREVENTED_CLAIM_TREND_ROUTE_BLOCKED_CLAIMS) - set(
        do_not_claim_yet
    )
    if missing_blocked:
        raise CityOpsContractError(
            "prevented-claim trend route preflight missing blocked claims: "
            f"{sorted(missing_blocked)}"
        )

    access_policy = preflight.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("prevented-claim trend route preflight audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("prevented-claim trend route preflight admin context drift")
    for flag, expected in ROUTE_FALSE_ACCESS_FLAGS.items():
        if access_policy.get(flag) is not expected:
            raise CityOpsContractError(
                f"prevented-claim trend route preflight promoted access {flag}"
            )
    for flag, expected in PREVENTED_CLAIM_TREND_ROUTE_FALSE_READINESS_FLAGS.items():
        if preflight.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(
                f"prevented-claim trend route preflight promoted readiness {flag}"
            )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
