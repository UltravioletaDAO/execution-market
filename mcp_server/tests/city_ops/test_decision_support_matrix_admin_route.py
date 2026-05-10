from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.decision_support_matrix_admin_route import (
    INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_PATH,
    INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_ROUTE_PREFLIGHT_FILENAME,
    INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_FILENAME,
    INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH,
    assert_internal_admin_decision_support_matrix_operator_display_adapter_response_contract,
    assert_internal_admin_decision_support_matrix_response_contract,
    build_internal_admin_decision_support_matrix_operator_display_adapter_route_preflight,
    build_internal_admin_decision_support_matrix_route_preflight,
    load_internal_admin_decision_support_matrix_operator_display_adapter,
    load_internal_admin_decision_support_matrix_card,
    router,
    write_internal_admin_decision_support_matrix_operator_display_adapter_route_preflight,
    write_internal_admin_decision_support_matrix_route_preflight,
)
from mcp_server.city_ops.decision_support_matrix_card import (
    DECISION_SUPPORT_MATRIX_CARD_FILENAME,
    load_decision_support_matrix_card,
)
from mcp_server.city_ops.decision_support_matrix_operator_consumer import (
    DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME,
)
from mcp_server.city_ops.decision_support_matrix_operator_display_adapter import (
    DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME,
    load_decision_support_matrix_operator_display_adapter,
)
from mcp_server.city_ops.decision_support_readiness_matrix import (
    DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
)

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
            INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH,
            headers=headers,
        )


async def get_display_adapter_response(
    *, headers: dict | None = None
) -> httpx.Response:
    app = FastAPI()
    app.include_router(router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(
            INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_PATH,
            headers=headers,
        )


@pytest.mark.anyio
async def test_internal_admin_route_requires_admin_auth(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_response()

    assert response.status_code == 401


@pytest.mark.anyio
async def test_internal_admin_route_rejects_wrong_admin_key(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_response(headers={"X-Admin-Key": "wrong"})

    assert response.status_code == 403


@pytest.mark.anyio
async def test_internal_admin_route_rejects_invalid_bearer_format(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_response(headers={"Authorization": "Basic supersecret"})

    assert response.status_code == 401


@pytest.mark.anyio
async def test_internal_admin_route_rejects_query_param_admin_key(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")
    app = FastAPI()
    app.include_router(router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            f"{INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH}?admin_key=supersecret"
        )

    assert response.status_code == 401
    assert "query-param auth is not allowed" in response.json()["detail"]


@pytest.mark.anyio
async def test_internal_admin_route_fails_closed_when_admin_auth_unconfigured(monkeypatch):
    monkeypatch.delenv("EM_ADMIN_KEY", raising=False)

    response = await get_response(headers={"X-Admin-Key": "anything"})

    assert response.status_code == 503


@pytest.mark.anyio
async def test_internal_admin_route_returns_persisted_card_payload_as_is(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")
    expected = load_decision_support_matrix_card()

    response = await get_response(
        headers={"X-Admin-Key": "supersecret", "X-Admin-Actor": "city-ops-test"},
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert response.json()["claim_cards"][0]["card"] == "safe_to_claim"
    assert response.json()["claim_cards"][1]["card"] == "do_not_claim_yet"
    assert response.json()["readiness"]["public_route_ready"] is False
    assert response.json()["readiness"]["dispatch_automation_ready"] is False
    assert response.json()["readiness"]["acontext_sink_ready"] is False
    assert response.json()["readiness"]["erc8004_reputation_ready"] is False
    assert response.json()["readiness"]["worker_skill_dna_ready"] is False
    assert response.json()["readiness"]["legal_or_regulator_ready"] is False
    assert response.json()["readiness"]["gps_or_metadata_exposure_allowed"] is False


@pytest.mark.anyio
async def test_internal_admin_route_accepts_bearer_admin_auth(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_response(headers={"Authorization": "Bearer supersecret"})

    assert response.status_code == 200
    assert response.json() == load_internal_admin_decision_support_matrix_card()


def test_response_contract_guard_refuses_claim_card_drift():
    card = copy.deepcopy(load_decision_support_matrix_card())
    card["claim_cards"] = list(reversed(card["claim_cards"]))

    with pytest.raises(CityOpsContractError, match="adjacent safe/blocked claim cards"):
        assert_internal_admin_decision_support_matrix_response_contract(card)


def test_router_exposes_only_internal_admin_get_route():
    matching_routes = [
        route
        for route in router.routes
        if getattr(route, "path", None) == INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH
    ]

    assert len(matching_routes) == 1
    assert matching_routes[0].methods == {"GET"}


def test_router_exposes_internal_admin_display_adapter_get_route():
    matching_routes = [
        route
        for route in router.routes
        if getattr(route, "path", None)
        == INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_PATH
    ]

    assert len(matching_routes) == 1
    assert matching_routes[0].methods == {"GET"}


@pytest.mark.anyio
async def test_internal_admin_display_adapter_route_requires_admin_auth(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_display_adapter_response()

    assert response.status_code == 401


@pytest.mark.anyio
async def test_internal_admin_display_adapter_route_returns_persisted_payload_as_is(
    monkeypatch,
):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")
    expected = load_decision_support_matrix_operator_display_adapter()

    response = await get_display_adapter_response(
        headers={"X-Admin-Key": "supersecret", "X-Admin-Actor": "city-ops-test"},
    )

    assert response.status_code == 200
    assert response.json() == expected
    assert response.json()["display_cards"][2]["card"] == "safe_to_claim"
    assert response.json()["display_cards"][3]["card"] == "do_not_claim_yet"
    assert response.json()["readiness"]["public_route_ready"] is False
    assert response.json()["readiness"]["dispatch_automation_ready"] is False
    assert response.json()["readiness"]["acontext_sink_ready"] is False
    assert response.json()["readiness"]["erc8004_reputation_ready"] is False
    assert response.json()["readiness"]["worker_skill_dna_ready"] is False
    assert response.json()["readiness"]["gps_or_metadata_exposure_allowed"] is False


@pytest.mark.anyio
async def test_internal_admin_display_adapter_route_accepts_bearer_admin_auth(
    monkeypatch,
):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    response = await get_display_adapter_response(
        headers={"Authorization": "Bearer supersecret"},
    )

    assert response.status_code == 200
    assert response.json() == load_internal_admin_decision_support_matrix_operator_display_adapter()


def test_internal_admin_route_preflight_is_mount_ready_without_external_claims():
    preflight = build_internal_admin_decision_support_matrix_route_preflight()

    assert preflight["route_probe"]["route_handler_registered"] is True
    assert preflight["route_probe"]["admin_auth_boundary_present"] is True
    assert preflight["route_probe"]["route_path"] == (
        INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH
    )
    assert preflight["readiness"]["route_mount_ready"] is True
    assert preflight["readiness"]["authenticated_internal_admin_route_ready"] is True
    assert preflight["readiness"]["route_response_verified"] is True
    assert preflight["access_policy"]["public_route_registered"] is False
    assert preflight["access_policy"]["customer_visible"] is False
    assert preflight["access_policy"]["dispatch_enabled"] is False
    assert preflight["access_policy"]["writes_live_acontext"] is False
    assert preflight["access_policy"]["emits_reputation_receipts"] is False
    assert preflight["access_policy"]["exposes_gps_or_metadata"] is False
    assert preflight["access_policy"]["publishes_worker_doctrine"] is False


def test_write_internal_admin_route_preflight_persists_mount_ready_artifact(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_MATRIX_CARD_FILENAME,
        tmp_path / DECISION_SUPPORT_MATRIX_CARD_FILENAME,
    )
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
        tmp_path / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
    )

    path = write_internal_admin_decision_support_matrix_route_preflight(
        artifact_dir=tmp_path
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_PREFLIGHT_FILENAME
    assert persisted["readiness"]["route_mount_ready"] is True


def test_internal_admin_display_adapter_route_preflight_is_mount_ready_without_external_claims():
    preflight = (
        build_internal_admin_decision_support_matrix_operator_display_adapter_route_preflight()
    )

    assert preflight["route_probe"]["route_handler_registered"] is True
    assert preflight["route_probe"]["admin_auth_boundary_present"] is True
    assert preflight["route_probe"]["route_path"] == (
        INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_PATH
    )
    assert preflight["readiness"]["route_mount_ready"] is True
    assert preflight["readiness"]["authenticated_internal_admin_route_ready"] is True
    assert preflight["readiness"]["route_response_verified"] is True
    assert preflight["access_policy"]["public_route_registered"] is False
    assert preflight["access_policy"]["customer_visible"] is False
    assert preflight["access_policy"]["dispatch_enabled"] is False
    assert preflight["access_policy"]["writes_live_acontext"] is False
    assert preflight["access_policy"]["emits_reputation_receipts"] is False
    assert preflight["access_policy"]["exposes_gps_or_metadata"] is False
    assert preflight["access_policy"]["publishes_worker_doctrine"] is False


def test_write_internal_admin_display_adapter_route_preflight_persists_artifact(
    tmp_path,
):
    for filename in [
        DECISION_SUPPORT_MATRIX_CARD_FILENAME,
        DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
        DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME,
        DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME,
    ]:
        shutil.copy(PROOF_BLOCK_DIR / filename, tmp_path / filename)

    path = write_internal_admin_decision_support_matrix_operator_display_adapter_route_preflight(
        artifact_dir=tmp_path
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == (
        tmp_path
        / INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_ROUTE_PREFLIGHT_FILENAME
    )
    assert persisted["readiness"]["route_mount_ready"] is True
    assert persisted["route_contract"]["returns_payload_as_is"] is True


def test_response_contract_guard_refuses_promoted_readiness():
    card = copy.deepcopy(load_decision_support_matrix_card())
    card["readiness"]["dispatch_automation_ready"] = True

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        assert_internal_admin_decision_support_matrix_response_contract(card)


def test_display_adapter_response_contract_refuses_promoted_readiness():
    adapter = copy.deepcopy(load_decision_support_matrix_operator_display_adapter())
    adapter["readiness"]["dispatch_automation_ready"] = True

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        assert_internal_admin_decision_support_matrix_operator_display_adapter_response_contract(
            adapter
        )


def test_display_adapter_response_contract_refuses_claim_card_drift():
    adapter = copy.deepcopy(load_decision_support_matrix_operator_display_adapter())
    adapter["display_cards"][2], adapter["display_cards"][3] = (
        adapter["display_cards"][3],
        adapter["display_cards"][2],
    )

    with pytest.raises(CityOpsContractError, match="adjacent safe/blocked"):
        assert_internal_admin_decision_support_matrix_operator_display_adapter_response_contract(
            adapter
        )


def test_loader_fails_closed_on_access_policy_drift(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_MATRIX_CARD_FILENAME,
        tmp_path / DECISION_SUPPORT_MATRIX_CARD_FILENAME,
    )
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
        tmp_path / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
    )
    path = tmp_path / DECISION_SUPPORT_MATRIX_CARD_FILENAME
    card = json.loads(path.read_text(encoding="utf-8"))
    card["access_policy"]["customer_visible"] = True
    path.write_text(json.dumps(card), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="access"):
        load_internal_admin_decision_support_matrix_card(artifact_dir=tmp_path)


def test_display_adapter_loader_fails_closed_on_access_policy_drift(tmp_path):
    for filename in [
        DECISION_SUPPORT_MATRIX_CARD_FILENAME,
        DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
        DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME,
        DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME,
    ]:
        shutil.copy(PROOF_BLOCK_DIR / filename, tmp_path / filename)
    path = tmp_path / DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME
    adapter = json.loads(path.read_text(encoding="utf-8"))
    adapter["access_policy"]["customer_visible"] = True
    path.write_text(json.dumps(adapter), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="access"):
        load_internal_admin_decision_support_matrix_operator_display_adapter(
            artifact_dir=tmp_path
        )
