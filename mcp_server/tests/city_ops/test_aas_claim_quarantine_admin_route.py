from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from mcp_server.city_ops.aas_claim_quarantine_admin_route import (
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PATH,
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME,
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SAFE_CLAIM,
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SCHEMA,
    assert_internal_admin_aas_claim_quarantine_response_contract,
    build_internal_admin_aas_claim_quarantine_route_mount_manifest,
    load_internal_admin_aas_claim_quarantine_read_surface,
    router,
    write_internal_admin_aas_claim_quarantine_route_mount_manifest,
)
from mcp_server.city_ops.aas_claim_quarantine_read_surface import (
    AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME,
    AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
    load_aas_claim_quarantine_read_surface,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
AAS_LADDER_DIR = FIXTURES / "aas_package_ladder"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def get_response(*, headers: dict | None = None) -> httpx.Response:
    app = FastAPI()
    app.include_router(router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(
            INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PATH,
            headers=headers,
        )


@pytest.mark.anyio
async def test_claim_quarantine_route_requires_admin_auth(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_response()

    assert response.status_code == 401


@pytest.mark.anyio
async def test_claim_quarantine_route_rejects_wrong_admin_key(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_response(headers={"X-Admin-Key": "wrong"})

    assert response.status_code == 403


@pytest.mark.anyio
async def test_claim_quarantine_route_fails_closed_when_admin_auth_unconfigured(monkeypatch):
    monkeypatch.delenv("EM_ADMIN_KEY", raising=False)

    response = await get_response(headers={"X-Admin-Key": "anything"})

    assert response.status_code == 503


@pytest.mark.anyio
async def test_claim_quarantine_route_returns_persisted_surface_as_is(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")
    expected = load_aas_claim_quarantine_read_surface()

    response = await get_response(
        headers={"X-Admin-Key": "supersecret", "X-Admin-Actor": "city-ops-test"},
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert response.json()["access_policy"]["public_route_registered"] is False
    assert response.json()["access_policy"]["customer_visible"] is False
    assert response.json()["access_policy"]["dispatch_enabled"] is False
    assert response.json()["access_policy"]["writes_live_acontext"] is False
    assert response.json()["access_policy"]["emits_reputation_receipts"] is False
    assert response.json()["readiness"]["customer_delivery_ready"] is False
    assert response.json()["readiness"]["publication_ready"] is False
    assert response.json()["readiness"]["live_acontext_runtime_parity_ready"] is False


@pytest.mark.anyio
async def test_claim_quarantine_route_accepts_bearer_admin_auth(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_response(headers={"Authorization": "Bearer supersecret"})

    assert response.status_code == 200
    assert response.json() == load_internal_admin_aas_claim_quarantine_read_surface()


def test_router_exposes_only_internal_admin_claim_quarantine_get_route():
    matching_routes = [
        route
        for route in router.routes
        if getattr(route, "path", None) == INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PATH
    ]

    assert len(matching_routes) == 1
    assert matching_routes[0].methods == {"GET"}


def test_claim_quarantine_response_contract_refuses_path_drift():
    surface = copy.deepcopy(load_aas_claim_quarantine_read_surface())
    surface["render_contract"]["suggested_internal_path"] = "/internal/admin/wrong"

    with pytest.raises(CityOpsContractError, match="path drift"):
        assert_internal_admin_aas_claim_quarantine_response_contract(surface)


def test_claim_quarantine_response_contract_refuses_customer_visibility():
    surface = copy.deepcopy(load_aas_claim_quarantine_read_surface())
    surface["access_policy"]["customer_visible"] = True

    with pytest.raises(CityOpsContractError, match="customer_visible"):
        assert_internal_admin_aas_claim_quarantine_response_contract(surface)


def test_claim_quarantine_route_mount_manifest_matches_fixture():
    manifest = build_internal_admin_aas_claim_quarantine_route_mount_manifest()
    fixture = json.loads(
        (AAS_LADDER_DIR / INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME).read_text(
            encoding="utf-8"
        )
    )

    assert manifest == fixture
    assert manifest["schema"] == INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SCHEMA
    assert manifest["mounted_routes"][0]["path"] == INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PATH
    assert manifest["readiness"]["app_level_router_include_smoke_passed"] is True
    assert manifest["readiness"]["public_route_ready"] is False
    assert manifest["readiness"]["customer_visible_catalog_ready"] is False
    assert manifest["readiness"]["dispatch_automation_ready"] is False
    assert manifest["readiness"]["live_acontext_ready"] is False
    assert manifest["readiness"]["erc8004_reputation_ready"] is False
    assert manifest["readiness"]["worker_skill_dna_ready"] is False
    assert AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM in manifest["claim_boundaries"]["safe_to_claim"]
    assert INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SAFE_CLAIM in manifest[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert "claim_quarantine_route_is_public_or_customer_route" in manifest[
        "claim_boundaries"
    ]["do_not_claim_yet"]


def test_write_claim_quarantine_route_mount_manifest_persists_fixture(tmp_path):
    shutil.copy(
        AAS_LADDER_DIR / AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME,
        tmp_path / AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME,
    )
    shutil.copy(
        AAS_LADDER_DIR / "aas_claim_quarantine_board.json",
        tmp_path / "aas_claim_quarantine_board.json",
    )

    path = write_internal_admin_aas_claim_quarantine_route_mount_manifest(artifact_dir=tmp_path)
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME
    assert persisted == build_internal_admin_aas_claim_quarantine_route_mount_manifest()


def test_claim_quarantine_route_mount_manifest_refuses_missing_route():
    with pytest.raises(CityOpsContractError, match="mount count drift"):
        build_internal_admin_aas_claim_quarantine_route_mount_manifest(app_routes=[])


def test_claim_quarantine_route_mount_manifest_refuses_public_route_promotion():
    manifest = build_internal_admin_aas_claim_quarantine_route_mount_manifest()
    manifest["readiness"]["public_route_ready"] = True

    # Exercise the validator via a deliberately stale fixture write path: mutating
    # the manifest should be caught when the public readiness flag is inspected by
    # the manifest builder contract in normal construction.
    with pytest.raises(CityOpsContractError, match="public_route_ready"):
        from mcp_server.city_ops.aas_claim_quarantine_admin_route import (
            _assert_internal_admin_aas_claim_quarantine_route_mount_manifest,
        )

        _assert_internal_admin_aas_claim_quarantine_route_mount_manifest(manifest)
