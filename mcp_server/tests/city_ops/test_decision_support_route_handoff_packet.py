import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.decision_support_matrix_admin_route import (
    INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_FILENAME,
    build_internal_admin_decision_support_matrix_route_mount_manifest,
)
from mcp_server.city_ops.decision_support_route_handoff_packet import (
    DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_FILENAME,
    DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_SAFE_CLAIM,
    DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_SCHEMA,
    build_decision_support_route_handoff_packet,
    load_internal_admin_route_mount_manifest,
    write_decision_support_route_handoff_packet_fixture,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_packet() -> dict:
    with (PROOF_BLOCK_DIR / DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_route_handoff_packet_matches_fixture():
    packet = build_decision_support_route_handoff_packet()

    assert packet == read_fixture_packet()
    assert packet["schema"] == DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_SCHEMA
    assert (
        packet["handoff_verdict"]
        == "route_boundary_handoff_ready_stop_route_expansion_until_live_transport_proof"
    )
    assert DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert "public_or_customer_route_ready" in packet["claim_boundaries"][
        "do_not_claim_yet"
    ]
    assert "live_acontext_transport_parity_landed" in packet["claim_boundaries"][
        "do_not_claim_yet"
    ]


def test_route_handoff_packet_names_patterns_and_next_actions():
    packet = build_decision_support_route_handoff_packet()
    patterns = {pattern["pattern"]: pattern for pattern in packet["coordination_patterns"]}

    assert patterns["artifact_route_boundary"]["status"] == "active"
    assert patterns["adjacent_claim_limits"]["status"] == "active"
    assert patterns["mount_smoke_is_not_product_readiness"]["status"] == "guardrail"
    assert patterns["stop_route_expansion_until_transport_truth"]["status"] == "recommended"
    assert packet["readiness"]["daytime_pickup_ready"] is True
    assert packet["readiness"]["route_expansion_paused"] is True
    assert packet["readiness"]["public_route_ready"] is False
    assert packet["readiness"]["acontext_sink_ready"] is False
    assert packet["readiness"]["runtime_parity_proven"] is False
    assert any(
        "exactly one live write/retrieve parity pass" in action
        for action in packet["recommended_next_actions"]
    )


def test_write_route_handoff_packet_persists_from_manifest(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_FILENAME,
        tmp_path / INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_FILENAME,
    )

    path = write_decision_support_route_handoff_packet_fixture(artifact_dir=tmp_path)
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_FILENAME
    assert persisted["readiness"]["source_manifest_verified"] is True
    assert persisted["handoff_cards"][2]["card"] == "safe_to_claim"
    assert persisted["handoff_cards"][3]["card"] == "do_not_claim_yet"


def test_load_route_mount_manifest_builds_when_missing(tmp_path):
    manifest = load_internal_admin_route_mount_manifest(artifact_dir=tmp_path)

    assert manifest == build_internal_admin_decision_support_matrix_route_mount_manifest()
    assert manifest["readiness"]["app_level_router_include_smoke_passed"] is True


def test_route_handoff_packet_refuses_public_route_promotion():
    manifest = copy.deepcopy(build_internal_admin_decision_support_matrix_route_mount_manifest())
    manifest["readiness"]["public_route_ready"] = True

    with pytest.raises(CityOpsContractError, match="public_route_ready"):
        build_decision_support_route_handoff_packet(route_mount_manifest=manifest)


def test_route_handoff_packet_refuses_route_count_drift():
    manifest = copy.deepcopy(build_internal_admin_decision_support_matrix_route_mount_manifest())
    manifest["mount_contract"]["mounted_route_count"] = 1

    with pytest.raises(CityOpsContractError, match="route-count drift"):
        build_decision_support_route_handoff_packet(route_mount_manifest=manifest)


def test_route_handoff_packet_refuses_claim_overlap():
    manifest = copy.deepcopy(build_internal_admin_decision_support_matrix_route_mount_manifest())
    claim = manifest["claim_boundaries"]["safe_to_claim"][0]
    manifest["claim_boundaries"]["do_not_claim_yet"].append(claim)

    with pytest.raises(CityOpsContractError, match="claim overlap"):
        build_decision_support_route_handoff_packet(route_mount_manifest=manifest)
