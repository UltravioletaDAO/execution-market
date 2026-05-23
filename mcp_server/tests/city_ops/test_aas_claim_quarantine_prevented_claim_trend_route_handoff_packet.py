from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_claim_quarantine_admin_route import (
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH,
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_FILENAME,
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SAFE_CLAIM,
    build_internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight,
)
from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_trend_read_surface import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM,
)
from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_trend_route_handoff_packet import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_FILENAME,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_SCHEMA,
    build_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet,
    load_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet,
    write_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
AAS_LADDER_DIR = FIXTURES / "aas_package_ladder"


def test_prevented_claim_trend_route_handoff_packet_matches_fixture():
    packet = build_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet()
    fixture = json.loads(
        (
            AAS_LADDER_DIR
            / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_FILENAME
        ).read_text(encoding="utf-8")
    )

    assert packet == fixture
    assert packet["schema"] == (
        AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_SCHEMA
    )
    assert packet["source_preflight"]["route_path"] == (
        INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_PATH
    )
    assert packet["readiness"]["handoff_packet_landed"] is True
    assert packet["readiness"]["route_expansion_paused"] is True
    assert packet["readiness"]["customer_delivery_ready"] is False
    assert packet["readiness"]["publication_ready"] is False
    assert packet["readiness"]["dispatch_ready"] is False
    assert packet["readiness"]["erc8004_reputation_ready"] is False
    assert packet["readiness"]["live_acontext_runtime_parity_ready"] is False
    assert packet["readiness"]["worker_skill_dna_ready"] is False
    assert AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert "trend_route_handoff_is_human_approval_record" in packet["claim_boundaries"][
        "do_not_claim_yet"
    ]
    assert "trend_route_handoff_authorizes_customer_delivery" in packet[
        "claim_boundaries"
    ]["do_not_claim_yet"]
    assert packet["handoff_cards"][2]["card"] == "safe_to_claim"
    assert packet["handoff_cards"][3]["card"] == "do_not_claim_yet"


def test_write_prevented_claim_trend_route_handoff_packet_persists_fixture(tmp_path):
    for source_path in AAS_LADDER_DIR.glob("*.json"):
        if source_path.name == (
            AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_FILENAME
        ):
            continue
        shutil.copy(source_path, tmp_path / source_path.name)

    path = write_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet(
        artifact_dir=tmp_path
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == (
        tmp_path
        / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_HANDOFF_PACKET_FILENAME
    )
    assert persisted == build_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet(
        artifact_dir=tmp_path
    )


def test_load_prevented_claim_trend_route_handoff_packet_validates_fixture():
    packet = load_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet()

    assert packet["handoff_verdict"].startswith("prevented_claim_trend_route_handoff")
    assert packet["source_preflight"]["file"] == (
        INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_ROUTE_PREFLIGHT_FILENAME
    )


def test_prevented_claim_trend_route_handoff_refuses_source_readiness_promotion():
    preflight = copy.deepcopy(
        build_internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight()
    )
    preflight["readiness"]["public_route_ready"] = True

    with pytest.raises(CityOpsContractError, match="public_route_ready"):
        build_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet(
            route_preflight=preflight
        )


def test_prevented_claim_trend_route_handoff_refuses_customer_visibility():
    preflight = copy.deepcopy(
        build_internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight()
    )
    preflight["access_policy"]["customer_visible"] = True

    with pytest.raises(CityOpsContractError, match="customer_visible"):
        build_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet(
            route_preflight=preflight
        )


def test_prevented_claim_trend_route_handoff_refuses_claim_overlap():
    preflight = copy.deepcopy(
        build_internal_admin_aas_claim_quarantine_prevented_claim_trend_route_preflight()
    )
    preflight["claim_boundaries"]["do_not_claim_yet"].append(
        preflight["claim_boundaries"]["safe_to_claim"][0]
    )

    with pytest.raises(CityOpsContractError, match="claim overlap"):
        build_aas_claim_quarantine_prevented_claim_trend_route_handoff_packet(
            route_preflight=preflight
        )
