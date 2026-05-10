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
    INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH,
    load_internal_admin_decision_support_matrix_card,
    router,
)
from mcp_server.city_ops.decision_support_matrix_card import (
    DECISION_SUPPORT_MATRIX_CARD_FILENAME,
    load_decision_support_matrix_card,
)
from mcp_server.city_ops.decision_support_matrix_operator_consumer import (
    DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME,
    DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SAFE_CLAIM,
    build_decision_support_matrix_operator_consumer,
    load_decision_support_matrix_operator_consumer,
    write_decision_support_matrix_operator_consumer_fixture,
)
from mcp_server.city_ops.decision_support_readiness_matrix import (
    DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def copy_required_artifacts(tmp_path: Path) -> None:
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_MATRIX_CARD_FILENAME,
        tmp_path / DECISION_SUPPORT_MATRIX_CARD_FILENAME,
    )
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
        tmp_path / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_operator_consumer_accepts_authenticated_route_response(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")
    app = FastAPI()
    app.include_router(router)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH,
            headers={"X-Admin-Key": "supersecret"},
        )

    assert response.status_code == 200
    consumer = build_decision_support_matrix_operator_consumer(
        route_payload=response.json()
    )

    assert consumer["readiness"]["internal_admin_route_consumed"] is True
    assert consumer["operator_consumer_sections"]["axis_cards"] == response.json()[
        "axis_cards"
    ]


def test_operator_consumer_consumes_only_internal_admin_route_payload():
    route_payload = load_internal_admin_decision_support_matrix_card()
    consumer = build_decision_support_matrix_operator_consumer(
        route_payload=route_payload
    )

    assert consumer["source_route"]["path"] == INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH
    assert consumer["source_route"]["consumes_only"] == [
        INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH
    ]
    assert consumer["source_route"]["semantic_reinterpretation_performed"] is False
    assert consumer["render_contract"]["network_route_registered"] is False
    assert consumer["operator_consumer_sections"]["axis_cards"] == route_payload[
        "axis_cards"
    ]
    assert consumer["operator_consumer_sections"]["claim_cards"] == route_payload[
        "claim_cards"
    ]
    assert consumer["operator_consumer_sections"]["readiness"] == route_payload[
        "readiness"
    ]


def test_operator_consumer_keeps_safe_and_blocked_claims_adjacent():
    consumer = build_decision_support_matrix_operator_consumer()

    assert DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SAFE_CLAIM in consumer[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert not (
        set(consumer["claim_boundaries"]["safe_to_claim"])
        & set(consumer["claim_boundaries"]["do_not_claim_yet"])
    )
    assert consumer["operator_consumer_sections"]["claim_cards"][0]["card"] == (
        "safe_to_claim"
    )
    assert consumer["operator_consumer_sections"]["claim_cards"][1]["card"] == (
        "do_not_claim_yet"
    )


def test_operator_consumer_refuses_external_readiness_flags():
    consumer = build_decision_support_matrix_operator_consumer()

    for flag in [
        "operator_ui_ready",
        "polished_operator_console_ready",
        "public_route_ready",
        "customer_visible_catalog_ready",
        "dispatch_automation_ready",
        "live_acontext_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "gps_or_metadata_exposure_allowed",
    ]:
        assert consumer["readiness"][flag] is False

    for flag in [
        "network_route_registered",
        "public_route_registered",
        "customer_visible",
        "dispatch_enabled",
        "writes_live_acontext",
        "emits_reputation_receipts",
        "exposes_gps_or_metadata",
    ]:
        assert consumer["access_policy"][flag] is False


def test_write_and_load_operator_consumer_fixture(tmp_path):
    copy_required_artifacts(tmp_path)

    path = write_decision_support_matrix_operator_consumer_fixture(
        artifact_dir=tmp_path
    )
    loaded = load_decision_support_matrix_operator_consumer(artifact_dir=tmp_path)

    assert path == tmp_path / DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME
    assert loaded == json.loads(path.read_text(encoding="utf-8"))
    assert loaded["readiness"]["operator_consumer_landed"] is True


def test_default_persisted_operator_consumer_loads():
    loaded = load_decision_support_matrix_operator_consumer()

    assert loaded["schema"] == "city_ops.decision_support_matrix_operator_consumer.v1"
    assert loaded["source_route"]["path"] == INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_PATH


def test_operator_consumer_refuses_promoted_route_payload():
    route_payload = copy.deepcopy(load_decision_support_matrix_card())
    route_payload["access_policy"]["customer_visible"] = True

    with pytest.raises(CityOpsContractError, match="access drift"):
        build_decision_support_matrix_operator_consumer(route_payload=route_payload)


def test_operator_consumer_loader_refuses_stale_digest(tmp_path):
    copy_required_artifacts(tmp_path)
    path = write_decision_support_matrix_operator_consumer_fixture(
        artifact_dir=tmp_path
    )
    consumer = json.loads(path.read_text(encoding="utf-8"))
    consumer["source_route"]["source_payload_digest"] = "stale"
    path.write_text(json.dumps(consumer), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="digest drift"):
        load_decision_support_matrix_operator_consumer(artifact_dir=tmp_path)


def test_operator_consumer_loader_refuses_pass_through_drift(tmp_path):
    copy_required_artifacts(tmp_path)
    path = write_decision_support_matrix_operator_consumer_fixture(
        artifact_dir=tmp_path
    )
    consumer = json.loads(path.read_text(encoding="utf-8"))
    consumer["operator_consumer_sections"]["recommended_next_action"] = "invent copy"
    path.write_text(json.dumps(consumer), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="pass-through section drift"):
        load_decision_support_matrix_operator_consumer(artifact_dir=tmp_path)
