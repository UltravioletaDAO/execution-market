import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_customer_facing_draft_packet import (
    PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME,
    PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM,
    build_phase1_customer_facing_draft_packet,
)
from mcp_server.city_ops.phase1_customer_output_schema_review_gate import REQUIRED_OFFER_ORDER
from mcp_server.city_ops.phase1_draft_packet_operator_review_decision import (
    PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME,
    PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM,
    PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SCHEMA,
    build_phase1_draft_packet_operator_review_decision,
    load_phase1_draft_packet_operator_review_decision,
    write_phase1_draft_packet_operator_review_decision,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_packet() -> dict:
    with (REVIEWED_FIXTURE_DIR / PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_draft_packet(tmp_path: Path) -> None:
    packet = build_phase1_customer_facing_draft_packet()
    (tmp_path / PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )


def test_draft_packet_operator_review_decision_matches_persisted_artifact():
    packet = build_phase1_draft_packet_operator_review_decision()

    assert packet == read_packet()
    assert load_phase1_draft_packet_operator_review_decision() == packet
    assert packet["schema"] == PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SCHEMA
    assert packet["scope"] == "internal_admin_publication_hold_decision_only"
    assert PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM in packet["safe_to_claim"]
    assert PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM in packet["safe_to_claim"]


def test_review_decision_records_hold_without_approval_or_publication():
    packet = build_phase1_draft_packet_operator_review_decision()

    assert packet["review_decision"] == "hold_not_approved_not_publishable"
    assert packet["operator_review_recorded"] is True
    assert packet["operator_review_granted"] is False
    assert packet["operator_publish_approval"] is False
    assert packet["customer_delivery_approval"] is False
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


def test_review_findings_are_verified_but_do_not_grant_approval():
    packet = build_phase1_draft_packet_operator_review_decision()

    assert packet["review_findings"]
    for finding in packet["review_findings"]:
        assert finding["verified"] is True
        assert finding["approval_granted"] is False


def test_offer_review_decisions_follow_offer_order_and_hold_each_offer():
    packet = build_phase1_draft_packet_operator_review_decision()

    assert packet["offer_order"] == REQUIRED_OFFER_ORDER
    assert [decision["offer"] for decision in packet["offer_review_decisions"]] == REQUIRED_OFFER_ORDER
    for decision in packet["offer_review_decisions"]:
        assert decision["review_decision"] == "hold_for_explicit_human_operator_review"
        assert decision["draft_ready_for_customer"] is False
        assert decision["draft_publishable"] is False
        assert decision["operator_publish_approval"] is False
        assert decision["customer_delivery_approval"] is False
        assert "final privacy/redaction review" in decision["required_before_send"]
        assert "operator publish approval" in decision["required_before_send"]
        assert "customer delivery approval" in decision["required_before_send"]
        assert "no dispatch or reputation claim check" in decision["required_before_send"]


def test_claim_boundaries_stay_adjacent_and_conservative():
    packet = build_phase1_draft_packet_operator_review_decision()
    key_order = list(packet.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert not set(packet["safe_to_claim"]) & set(packet["do_not_claim_yet"])
    assert "operator_review_granted" in packet["do_not_claim_yet"]
    assert "operator_publish_approval" in packet["do_not_claim_yet"]
    assert "customer_delivery_approval" in packet["do_not_claim_yet"]
    assert "publication_approved" in packet["do_not_claim_yet"]
    assert "public_service_catalog_ready" in packet["do_not_claim_yet"]
    assert "erc8004_reputation_ready" in packet["do_not_claim_yet"]
    assert "exact_gps_or_raw_metadata_exposure_allowed" in packet["do_not_claim_yet"]


def test_write_draft_packet_operator_review_decision_persists_valid_artifact(tmp_path):
    seed_draft_packet(tmp_path)

    path = write_phase1_draft_packet_operator_review_decision(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME
    assert load_phase1_draft_packet_operator_review_decision(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_publication_approval_flip_fails_closed():
    source = build_phase1_customer_facing_draft_packet()
    source["publication_approved"] = True

    with pytest.raises(CityOpsContractError, match="source promoted readiness"):
        build_phase1_draft_packet_operator_review_decision(draft_packet=source)


def test_source_draft_card_publishable_flip_fails_closed():
    source = build_phase1_customer_facing_draft_packet()
    source["draft_cards"][0]["draft_publishable"] = True

    with pytest.raises(CityOpsContractError, match="source card promoted readiness"):
        build_phase1_draft_packet_operator_review_decision(draft_packet=source)


def test_loader_fails_closed_on_publication_approved_flip(tmp_path):
    packet = build_phase1_draft_packet_operator_review_decision()
    packet["publication_approved"] = True
    (tmp_path / PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_phase1_draft_packet_operator_review_decision(fixture_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    packet = build_phase1_draft_packet_operator_review_decision()
    packet["safe_to_claim"].append("operator_publish_approval")
    (tmp_path / PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_phase1_draft_packet_operator_review_decision(fixture_dir=tmp_path)


def test_loader_fails_closed_on_offer_decision_approval_flip(tmp_path):
    packet = build_phase1_draft_packet_operator_review_decision()
    packet["offer_review_decisions"][1]["operator_publish_approval"] = True
    (tmp_path / PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="offer promoted readiness"):
        load_phase1_draft_packet_operator_review_decision(fixture_dir=tmp_path)


def test_source_missing_blocked_claim_fails_closed():
    source = copy.deepcopy(build_phase1_customer_facing_draft_packet())
    source["do_not_claim_yet"] = [
        claim
        for claim in source["do_not_claim_yet"]
        if claim != "publication_approved"
    ]

    with pytest.raises(CityOpsContractError, match="source missing blocked claims"):
        build_phase1_draft_packet_operator_review_decision(draft_packet=source)
