import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_customer_facing_draft_packet import (
    PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME,
    PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM,
    PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SCHEMA,
    build_phase1_customer_facing_draft_packet,
    load_phase1_customer_facing_draft_packet,
    write_phase1_customer_facing_draft_packet,
)
from mcp_server.city_ops.phase1_customer_output_schema_review_gate import REQUIRED_OFFER_ORDER
from mcp_server.city_ops.phase1_sample_publication_approval_checklist import (
    PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME,
    PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SAFE_CLAIM,
    build_phase1_sample_publication_approval_checklist,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_packet() -> dict:
    with (REVIEWED_FIXTURE_DIR / PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_checklist(tmp_path: Path) -> None:
    packet = build_phase1_sample_publication_approval_checklist()
    (tmp_path / PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )


def test_customer_facing_draft_packet_matches_persisted_artifact():
    packet = build_phase1_customer_facing_draft_packet()

    assert packet == read_packet()
    assert load_phase1_customer_facing_draft_packet() == packet
    assert packet["schema"] == PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SCHEMA
    assert packet["scope"] == "internal_admin_customer_facing_draft_review_only"
    assert PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SAFE_CLAIM in packet["safe_to_claim"]
    assert PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM in packet["safe_to_claim"]


def test_draft_packet_is_created_but_not_ready_or_publishable():
    packet = build_phase1_customer_facing_draft_packet()

    assert packet["draft_packet_status"] == "draft_created_not_approved_not_publishable"
    assert packet["customer_facing_draft_packet_created"] is True
    assert packet["customer_copy_created"] is False
    assert packet["customer_copy_ready"] is False
    assert packet["customer_visible_catalog_ready"] is False
    assert packet["public_service_catalog_ready"] is False
    assert packet["controlled_concierge_pilot_ready"] is False
    assert packet["customer_pilot_exposure_allowed"] is False
    assert packet["front_door_sku_ready"] is False
    assert packet["draft_packet_publishable"] is False
    assert packet["draft_packet_publication_ready"] is False
    assert packet["sample_outputs_publishable"] is False
    assert packet["publication_approved"] is False
    assert packet["publish_route_ready"] is False
    assert packet["live_acontext_ready"] is False
    assert packet["runtime_parity_proven"] is False
    assert packet["autonomous_dispatch_ready"] is False
    assert packet["reputation_ready"] is False
    assert packet["worker_skill_dna_ready"] is False
    assert packet["worker_copyable_doctrine_ready"] is False
    assert packet["exact_gps_or_raw_metadata_exposure_allowed"] is False


def test_draft_cards_follow_offer_order_and_require_reviews():
    packet = build_phase1_customer_facing_draft_packet()

    assert packet["offer_order"] == REQUIRED_OFFER_ORDER
    assert [card["offer"] for card in packet["draft_cards"]] == REQUIRED_OFFER_ORDER
    for card in packet["draft_cards"]:
        assert card["draft_ready_for_customer"] is False
        assert card["draft_publishable"] is False
        assert card["operator_publish_approval"] is False
        assert card["customer_delivery_approval"] is False
        assert card["source_publication_ready"] is False
        assert card["source_sample_publishable"] is False
        assert "operator publish approval" in card["required_before_send"]
        assert "customer delivery approval" in card["required_before_send"]
        assert "blocked-claim adjacency check" in card["required_before_send"]
        assert "no dispatch or reputation claim check" in card["required_before_send"]


def test_claim_boundaries_stay_adjacent_and_conservative():
    packet = build_phase1_customer_facing_draft_packet()
    key_order = list(packet.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert not set(packet["safe_to_claim"]) & set(packet["do_not_claim_yet"])
    assert "draft_packet_publication_ready" in packet["do_not_claim_yet"]
    assert "publication_approved" in packet["do_not_claim_yet"]
    assert "customer_copy_ready" in packet["do_not_claim_yet"]
    assert "public_service_catalog_ready" in packet["do_not_claim_yet"]
    assert "erc8004_reputation_ready" in packet["do_not_claim_yet"]
    assert "exact_gps_or_raw_metadata_exposure_allowed" in packet["do_not_claim_yet"]


def test_write_customer_facing_draft_packet_persists_valid_artifact(tmp_path):
    seed_checklist(tmp_path)

    path = write_phase1_customer_facing_draft_packet(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME
    assert load_phase1_customer_facing_draft_packet(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_publication_approval_flip_fails_closed():
    source = build_phase1_sample_publication_approval_checklist()
    source["publication_approved"] = True

    with pytest.raises(CityOpsContractError, match="source promoted readiness"):
        build_phase1_customer_facing_draft_packet(checklist=source)


def test_source_approval_gate_flip_fails_closed():
    source = build_phase1_sample_publication_approval_checklist()
    source["approval_gates_status"]["operator_publish_approval_required"]["verified"] = True

    with pytest.raises(CityOpsContractError, match="source approval gate promoted"):
        build_phase1_customer_facing_draft_packet(checklist=source)


def test_source_offer_publishability_flip_fails_closed():
    source = build_phase1_sample_publication_approval_checklist()
    source["offer_publication_reviews"][0]["publication_ready"] = True

    with pytest.raises(CityOpsContractError, match="source offer promoted readiness"):
        build_phase1_customer_facing_draft_packet(checklist=source)


def test_loader_fails_closed_on_publication_approved_flip(tmp_path):
    packet = build_phase1_customer_facing_draft_packet()
    packet["publication_approved"] = True
    (tmp_path / PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_phase1_customer_facing_draft_packet(fixture_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    packet = build_phase1_customer_facing_draft_packet()
    packet["safe_to_claim"].append("publication_approved")
    (tmp_path / PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_phase1_customer_facing_draft_packet(fixture_dir=tmp_path)


def test_loader_fails_closed_on_draft_card_publishability_flip(tmp_path):
    packet = build_phase1_customer_facing_draft_packet()
    packet["draft_cards"][1]["draft_publishable"] = True
    (tmp_path / PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="card promoted readiness"):
        load_phase1_customer_facing_draft_packet(fixture_dir=tmp_path)


def test_source_missing_blocked_claim_fails_closed():
    source = copy.deepcopy(build_phase1_sample_publication_approval_checklist())
    source["do_not_claim_yet"] = [
        claim
        for claim in source["do_not_claim_yet"]
        if claim != "customer_copy_ready"
    ]

    with pytest.raises(CityOpsContractError, match="source missing blocked claims"):
        build_phase1_customer_facing_draft_packet(checklist=source)
