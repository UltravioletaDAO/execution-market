from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_system_integration_flywheel_admin_route import (
    INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH,
    INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME,
    INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SAFE_CLAIM,
    build_internal_admin_aas_system_integration_flywheel_route_preflight,
)
from mcp_server.city_ops.aas_system_integration_flywheel_read_surface import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM,
)
from mcp_server.city_ops.aas_system_integration_flywheel_route_handoff_packet import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SCHEMA,
    build_aas_system_integration_flywheel_route_handoff_packet,
    load_aas_system_integration_flywheel_route_handoff_packet,
    write_aas_system_integration_flywheel_route_handoff_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def test_system_integration_flywheel_route_handoff_packet_matches_fixture():
    packet = build_aas_system_integration_flywheel_route_handoff_packet()
    fixture = json.loads(
        (
            PROOF_BLOCK_DIR
            / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME
        ).read_text(encoding="utf-8")
    )

    assert packet == fixture
    assert packet["schema"] == AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SCHEMA
    assert packet["source_preflight"]["route_path"] == (
        INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_PATH
    )
    assert packet["readiness"]["handoff_packet_landed"] is True
    assert packet["readiness"]["route_expansion_paused"] is True
    assert packet["readiness"]["customer_delivery_ready"] is False
    assert packet["readiness"]["publication_ready"] is False
    assert packet["readiness"]["dispatch_ready"] is False
    assert packet["readiness"]["erc8004_reputation_ready"] is False
    assert packet["readiness"]["live_acontext_runtime_parity_ready"] is False
    assert packet["readiness"]["worker_skill_dna_ready"] is False
    assert AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert "system_integration_flywheel_route_handoff_authorizes_customer_delivery" in packet[
        "claim_boundaries"
    ]["do_not_claim_yet"]
    assert "system_integration_flywheel_route_handoff_proves_live_acontext_or_runtime_parity" in packet[
        "claim_boundaries"
    ]["do_not_claim_yet"]
    assert packet["handoff_cards"][2]["card"] == "safe_to_claim"
    assert packet["handoff_cards"][3]["card"] == "do_not_claim_yet"


def test_write_system_integration_flywheel_route_handoff_packet_persists_fixture(tmp_path):
    for source_path in PROOF_BLOCK_DIR.glob("*.json"):
        if source_path.name == AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME:
            continue
        shutil.copy(source_path, tmp_path / source_path.name)

    path = write_aas_system_integration_flywheel_route_handoff_packet(
        artifact_dir=tmp_path
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_HANDOFF_PACKET_FILENAME
    assert persisted == build_aas_system_integration_flywheel_route_handoff_packet(
        artifact_dir=tmp_path
    )


def test_load_system_integration_flywheel_route_handoff_packet_validates_fixture():
    packet = load_aas_system_integration_flywheel_route_handoff_packet()

    assert packet["handoff_verdict"].startswith(
        "system_integration_flywheel_route_handoff_ready"
    )
    assert packet["source_preflight"]["file"] == (
        INTERNAL_ADMIN_AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_PREFLIGHT_FILENAME
    )


def test_system_integration_flywheel_route_handoff_refuses_source_readiness_promotion():
    preflight = copy.deepcopy(
        build_internal_admin_aas_system_integration_flywheel_route_preflight()
    )
    preflight["readiness"]["live_acontext_ready"] = True

    with pytest.raises(CityOpsContractError, match="live_acontext_ready"):
        build_aas_system_integration_flywheel_route_handoff_packet(
            route_preflight=preflight
        )


def test_system_integration_flywheel_route_handoff_refuses_customer_visibility():
    preflight = copy.deepcopy(
        build_internal_admin_aas_system_integration_flywheel_route_preflight()
    )
    preflight["access_policy"]["customer_visible"] = True

    with pytest.raises(CityOpsContractError, match="customer_visible"):
        build_aas_system_integration_flywheel_route_handoff_packet(
            route_preflight=preflight
        )


def test_system_integration_flywheel_route_handoff_refuses_claim_overlap():
    preflight = copy.deepcopy(
        build_internal_admin_aas_system_integration_flywheel_route_preflight()
    )
    preflight["claim_boundaries"]["do_not_claim_yet"].append(
        preflight["claim_boundaries"]["safe_to_claim"][0]
    )

    with pytest.raises(CityOpsContractError, match="claim boundary overlap|claim overlap"):
        build_aas_system_integration_flywheel_route_handoff_packet(
            route_preflight=preflight
        )
