from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_claim_quarantine_admin_route import (
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME,
    build_internal_admin_aas_claim_quarantine_route_mount_manifest,
)
from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_panel import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
    build_aas_claim_quarantine_prevented_claim_panel,
)
from mcp_server.city_ops.aas_claim_quarantine_route_panel_handoff_packet import (
    AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME,
    AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SCHEMA,
    HANDOFF_BLOCKED_CLAIMS,
    build_aas_claim_quarantine_route_panel_handoff_packet,
    load_aas_claim_quarantine_route_mount_manifest,
    load_aas_claim_quarantine_route_panel_handoff_packet,
    write_aas_claim_quarantine_route_panel_handoff_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_packet() -> dict:
    with (ARTIFACT_DIR / AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    for source_path in ARTIFACT_DIR.glob("*.json"):
        if source_path.name == AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME:
            continue
        (tmp_path / source_path.name).write_text(
            source_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def test_route_panel_handoff_packet_matches_persisted_artifact_and_loader():
    packet = build_aas_claim_quarantine_route_panel_handoff_packet()

    assert packet == read_packet()
    assert load_aas_claim_quarantine_route_panel_handoff_packet() == packet
    assert packet["schema"] == AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SCHEMA
    assert packet["scope"] == "internal_admin_route_and_prevented_claim_panel_pickup_only"
    assert (
        packet["handoff_verdict"]
        == "claim_quarantine_route_panel_handoff_ready_stop_customer_dispatch_expansion"
    )
    assert AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_handoff_cards_keep_route_panel_and_claim_boundaries_adjacent():
    packet = build_aas_claim_quarantine_route_panel_handoff_packet()
    cards = packet["handoff_cards"]

    assert [card["card"] for card in cards[:5]] == [
        "route_mount_manifest",
        "prevented_claim_panel",
        "safe_to_claim",
        "do_not_claim_yet",
        "next_smallest_proof",
    ]
    assert cards[0]["mounted_route_count"] == 1
    assert cards[0]["routes"][0]["path"] == "/internal/admin/city-ops/aas-claim-quarantine"
    assert cards[1]["prevented_claim_count"] == 30
    assert cards[2]["values"] == packet["claim_boundaries"]["safe_to_claim"]
    assert cards[3]["values"] == packet["claim_boundaries"]["do_not_claim_yet"]


def test_handoff_keeps_prevented_claims_blocked_and_names_next_proofs():
    panel = build_aas_claim_quarantine_prevented_claim_panel()
    packet = build_aas_claim_quarantine_route_panel_handoff_packet(prevented_claim_panel=panel)
    prevented = set(panel["claim_boundary_footer"]["prevented_claims"])
    boundaries = packet["claim_boundaries"]

    assert prevented
    assert not prevented & set(boundaries["safe_to_claim"])
    assert prevented <= set(boundaries["do_not_claim_yet"])
    for claim in HANDOFF_BLOCKED_CLAIMS:
        assert claim in boundaries["do_not_claim_yet"]
        assert claim not in boundaries["safe_to_claim"]
    assert packet["claim_boundary_footer"]["prevented_claim_count"] == 30
    assert any(
        "human_operator_selected_boundary_approval_record" in value
        for value in packet["handoff_cards"][4]["values"]
    )


def test_handoff_preserves_internal_admin_false_readiness_and_access_flags():
    packet = build_aas_claim_quarantine_route_panel_handoff_packet()

    assert packet["derived_from"]["read_only"] is True
    assert packet["derived_from"]["adds_route"] is False
    assert packet["derived_from"]["semantic_reinterpretation_performed"] is False
    assert packet["access_policy"]["audience"] == "internal_admin_only"
    assert packet["access_policy"]["requires_admin_context"] is True
    for flag in [
        "public_route_registered",
        "catalog_route_registered",
        "customer_visible",
        "worker_visible",
        "dispatch_enabled",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "emits_reputation_receipts",
        "exposes_gps_or_metadata",
        "publishes_worker_doctrine",
    ]:
        assert packet["access_policy"][flag] is False
    for flag in [
        "customer_copy_ready",
        "customer_delivery_ready",
        "publication_ready",
        "public_or_catalog_route_ready",
        "dispatch_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "live_acontext_runtime_parity_ready",
        "payment_or_production_reverified",
        "exact_gps_or_raw_metadata_release_ready",
        "domain_authority_ready",
        "worker_copyable_doctrine_ready",
    ]:
        assert packet["readiness"][flag] is False


def test_coordination_patterns_explain_why_this_is_only_pickup_artifact():
    packet = build_aas_claim_quarantine_route_panel_handoff_packet()
    patterns = {item["pattern"]: item for item in packet["coordination_patterns"]}

    assert patterns["single_pickup_artifact"]["status"] == "active"
    assert patterns["route_mount_is_not_customer_authority"]["status"] == "guardrail"
    assert patterns["prevented_claims_are_not_approvals"]["status"] == "guardrail"
    assert patterns["adjacent_safe_and_blocked_claims"]["status"] == "active"
    assert any("Run the focused route/panel/handoff gate" in action for action in packet["recommended_next_actions"])
    assert any("Do not create customer copy" in action for action in packet["not_next_actions"])


def test_write_handoff_packet_persists_from_sources(tmp_path):
    seed_sources(tmp_path)

    path = write_aas_claim_quarantine_route_panel_handoff_packet(artifact_dir=tmp_path)
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME
    assert persisted["readiness"]["source_route_manifest_verified"] is True
    assert persisted["readiness"]["source_prevented_panel_verified"] is True
    assert persisted["handoff_cards"][2]["card"] == "safe_to_claim"
    assert persisted["handoff_cards"][3]["card"] == "do_not_claim_yet"


def test_load_route_manifest_builds_when_missing(tmp_path):
    manifest = load_aas_claim_quarantine_route_mount_manifest(artifact_dir=tmp_path)

    assert manifest == build_internal_admin_aas_claim_quarantine_route_mount_manifest()
    assert manifest["readiness"]["expected_route_registered"] is True


def test_handoff_refuses_public_route_promotion():
    manifest = copy.deepcopy(build_internal_admin_aas_claim_quarantine_route_mount_manifest())
    manifest["access_policy"]["public_route_registered"] = True

    with pytest.raises(CityOpsContractError, match="public_route_registered"):
        build_aas_claim_quarantine_route_panel_handoff_packet(route_mount_manifest=manifest)


def test_handoff_refuses_prevented_claim_promotion():
    panel = copy.deepcopy(build_aas_claim_quarantine_prevented_claim_panel())
    claim = panel["claim_boundary_footer"]["prevented_claims"][0]
    panel["claim_boundaries"]["safe_to_claim"].append(claim)

    with pytest.raises(CityOpsContractError, match="safe prevented claim"):
        build_aas_claim_quarantine_route_panel_handoff_packet(prevented_claim_panel=panel)


def test_handoff_refuses_claim_overlap():
    manifest = copy.deepcopy(build_internal_admin_aas_claim_quarantine_route_mount_manifest())
    claim = manifest["claim_boundaries"]["safe_to_claim"][0]
    manifest["claim_boundaries"]["do_not_claim_yet"].append(claim)

    with pytest.raises(CityOpsContractError, match="claim overlap"):
        build_aas_claim_quarantine_route_panel_handoff_packet(route_mount_manifest=manifest)
