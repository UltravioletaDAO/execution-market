from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from mcp_server.city_ops.aas_system_integration_flywheel_admin_route import (
    INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH,
    INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME,
    INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SAFE_CLAIM,
    INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SCHEMA,
    ROUTE_BLOCKED_CLAIMS,
    assert_internal_admin_aas_system_integration_flywheel_response_contract,
    build_internal_admin_aas_system_integration_flywheel_route_preflight,
    load_internal_admin_aas_system_integration_flywheel_read_surface,
    router,
    write_internal_admin_aas_system_integration_flywheel_route_preflight,
)
from mcp_server.city_ops.aas_system_integration_flywheel_read_surface import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM,
    load_aas_system_integration_flywheel_read_surface,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def get_response(*, headers: dict | None = None) -> httpx.Response:
    app = FastAPI()
    app.include_router(router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(
            INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH,
            headers=headers,
        )


@pytest.mark.anyio
async def test_system_integration_flywheel_route_requires_admin_auth(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_response()

    assert response.status_code == 401


@pytest.mark.anyio
async def test_system_integration_flywheel_route_rejects_wrong_admin_key(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_response(headers={"X-Admin-Key": "wrong"})

    assert response.status_code == 403


@pytest.mark.anyio
async def test_system_integration_flywheel_route_fails_closed_when_auth_unconfigured(
    monkeypatch,
):
    monkeypatch.delenv("EM_ADMIN_KEY", raising=False)

    response = await get_response(headers={"X-Admin-Key": "anything"})

    assert response.status_code == 503


@pytest.mark.anyio
async def test_system_integration_flywheel_route_returns_persisted_surface_as_is(
    monkeypatch,
):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")
    expected = load_aas_system_integration_flywheel_read_surface()

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
    assert response.json()["readiness"]["public_route_ready"] is False
    assert response.json()["readiness"]["autonomous_dispatch_ready"] is False
    assert response.json()["readiness"]["runtime_parity_proven"] is False


@pytest.mark.anyio
async def test_system_integration_flywheel_route_accepts_bearer_admin_auth(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_response(headers={"Authorization": "Bearer supersecret"})

    assert response.status_code == 200
    assert response.json() == load_internal_admin_aas_system_integration_flywheel_read_surface()


def test_router_exposes_only_internal_admin_system_integration_flywheel_get_route():
    matching_routes = [
        route
        for route in router.routes
        if getattr(route, "path", None) == INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH
    ]

    assert len(matching_routes) == 1
    assert matching_routes[0].methods == {"GET"}


def test_system_integration_flywheel_response_contract_refuses_customer_visibility():
    surface = copy.deepcopy(load_aas_system_integration_flywheel_read_surface())
    surface["access_policy"]["customer_visible"] = True

    with pytest.raises(CityOpsContractError, match="customer_visible"):
        assert_internal_admin_aas_system_integration_flywheel_response_contract(surface)


def test_system_integration_flywheel_response_contract_refuses_live_runtime_promotion():
    surface = copy.deepcopy(load_aas_system_integration_flywheel_read_surface())
    surface["readiness"]["runtime_parity_proven"] = True

    with pytest.raises(CityOpsContractError, match="runtime_parity_proven"):
        assert_internal_admin_aas_system_integration_flywheel_response_contract(surface)


def test_system_integration_flywheel_response_contract_refuses_path_drift():
    surface = copy.deepcopy(load_aas_system_integration_flywheel_read_surface())
    surface["render_contract"]["suggested_internal_path"] = "/internal/admin/wrong"

    with pytest.raises(CityOpsContractError, match="path drift"):
        assert_internal_admin_aas_system_integration_flywheel_response_contract(surface)


def test_system_integration_flywheel_route_preflight_matches_fixture():
    preflight = build_internal_admin_aas_system_integration_flywheel_route_preflight()
    fixture = json.loads(
        (
            PROOF_BLOCK_DIR
            / INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME
        ).read_text(encoding="utf-8")
    )

    assert preflight == fixture
    assert preflight["schema"] == (
        INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SCHEMA
    )
    assert preflight["mounted_routes"][0]["path"] == (
        INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH
    )
    assert preflight["route_contract"]["required_response_source"] == (
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME
    )
    assert preflight["readiness"]["route_preflight_landed"] is True
    assert preflight["readiness"]["public_route_ready"] is False
    assert preflight["readiness"]["customer_visible_catalog_ready"] is False
    assert preflight["readiness"]["dispatch_automation_ready"] is False
    assert preflight["readiness"]["live_acontext_ready"] is False
    assert preflight["readiness"]["erc8004_reputation_ready"] is False
    assert preflight["readiness"][
        "emergency_safety_repair_insurance_sla_official_report_or_fault_liability_ready"
    ] is False
    assert AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM in preflight[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SAFE_CLAIM in preflight[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert "system_integration_flywheel_route_is_public_or_customer_route" in preflight[
        "claim_boundaries"
    ]["do_not_claim_yet"]
    assert set(ROUTE_BLOCKED_CLAIMS) <= set(
        preflight["claim_boundaries"]["do_not_claim_yet"]
    )


def test_write_system_integration_flywheel_route_preflight_persists_fixture(tmp_path):
    for source_path in PROOF_BLOCK_DIR.glob("*.json"):
        if source_path.name == (
            INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME
        ):
            continue
        shutil.copy(source_path, tmp_path / source_path.name)

    path = write_internal_admin_aas_system_integration_flywheel_route_preflight(
        artifact_dir=tmp_path
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == (
        tmp_path / INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME
    )
    assert persisted == build_internal_admin_aas_system_integration_flywheel_route_preflight(
        artifact_dir=tmp_path
    )


def test_system_integration_flywheel_route_preflight_refuses_missing_route():
    with pytest.raises(CityOpsContractError, match="mount count drift"):
        build_internal_admin_aas_system_integration_flywheel_route_preflight(
            app_routes=[]
        )


def test_system_integration_flywheel_route_preflight_refuses_customer_route_promotion():
    preflight = build_internal_admin_aas_system_integration_flywheel_route_preflight()
    surface = load_aas_system_integration_flywheel_read_surface()
    preflight["access_policy"]["customer_visible"] = True

    from mcp_server.city_ops.aas_system_integration_flywheel_admin_route import (  # noqa: PLC0415
        _assert_internal_admin_aas_system_integration_flywheel_route_preflight,
    )

    with pytest.raises(CityOpsContractError, match="customer_visible"):
        _assert_internal_admin_aas_system_integration_flywheel_route_preflight(
            preflight, surface
        )
