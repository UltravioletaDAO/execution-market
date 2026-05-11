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
from mcp_server.city_ops.phase1_draft_packet_operator_review_decision import (
    PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME,
    PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM,
    build_phase1_draft_packet_operator_review_decision,
)
from mcp_server.city_ops.phase1_offer_card_human_operator_approval_record import (
    APPROVED_OFFER,
    AUTHORIZED_DELIVERY_PATH,
    PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME,
    PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
    PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA,
    REQUIRED_BLOCKED_CLAIMS,
    REQUIRED_REDACTION_CHECKS,
    build_phase1_offer_card_human_operator_approval_record,
    load_phase1_offer_card_human_operator_approval_record,
    write_phase1_offer_card_human_operator_approval_record,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_packet() -> dict:
    with (REVIEWED_FIXTURE_DIR / PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    draft = build_phase1_customer_facing_draft_packet()
    decision = build_phase1_draft_packet_operator_review_decision(draft_packet=draft)
    (tmp_path / PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME).write_text(
        json.dumps(draft), encoding="utf-8"
    )
    (tmp_path / PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )


def test_offer_card_human_operator_approval_record_matches_persisted_artifact():
    packet = build_phase1_offer_card_human_operator_approval_record()

    assert packet == read_packet()
    assert load_phase1_offer_card_human_operator_approval_record() == packet
    assert packet["schema"] == PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA
    assert packet["scope"] == "internal_admin_single_offer_card_human_approval_record_only"
    assert PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM in packet["safe_to_claim"]
    assert PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM in packet["safe_to_claim"]
    assert PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM in packet["safe_to_claim"]


def test_approval_record_names_exactly_one_approved_offer_card_text_boundary():
    packet = build_phase1_offer_card_human_operator_approval_record()
    card = packet["approved_offer_card"]

    assert packet["human_operator_approval_recorded"] is True
    assert packet["approved_offer_count"] == 1
    assert packet["approved_offer"] == APPROVED_OFFER == "counter_reality_check"
    assert card["offer"] == APPROVED_OFFER
    assert card["approved_text_fields"] == [
        "draft_title",
        "customer_safe_positioning",
        "draft_sections",
        "must_keep_limitations",
    ]
    assert card["approved_title_text"] == "Counter Reality Check — bounded status draft"
    assert "What was checked" in card["approved_section_names"]
    assert "What this does not prove" in card["approved_section_names"]
    assert card["approval_boundary"] == "text_shape_only_not_customer_copy_not_publication"


def test_redactions_and_authorized_delivery_path_are_record_boundaries_only():
    packet = build_phase1_offer_card_human_operator_approval_record()

    assert [item["check"] for item in packet["redactions_passed"]] == REQUIRED_REDACTION_CHECKS
    assert all(item["passed"] is True for item in packet["redactions_passed"])
    assert packet["authorized_delivery_path"] == {
        "path": AUTHORIZED_DELIVERY_PATH,
        "authorized_for": "internal_admin_operator_review_queue",
        "customer_delivery_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
    }


def test_publication_customer_delivery_dispatch_reputation_and_metadata_stay_blocked():
    packet = build_phase1_offer_card_human_operator_approval_record()

    for flag in [
        "operator_publish_approval",
        "customer_delivery_approval",
        "customer_copy_created",
        "customer_copy_ready",
        "customer_visible_catalog_ready",
        "public_service_catalog_ready",
        "controlled_concierge_pilot_ready",
        "customer_pilot_exposure_allowed",
        "front_door_sku_ready",
        "draft_packet_publishable",
        "draft_packet_publication_ready",
        "sample_outputs_publishable",
        "publication_approved",
        "publish_route_ready",
        "live_acontext_ready",
        "runtime_parity_proven",
        "autonomous_dispatch_ready",
        "reputation_ready",
        "worker_skill_dna_ready",
        "worker_copyable_doctrine_ready",
        "exact_gps_or_raw_metadata_exposure_allowed",
    ]:
        assert packet[flag] is False

    assert packet["still_blocked_claims"] == packet["do_not_claim_yet"]
    for claim in REQUIRED_BLOCKED_CLAIMS:
        assert claim in packet["still_blocked_claims"]
    assert "publication_approved" in packet["still_blocked_claims"]
    assert "customer_delivery_approval" in packet["still_blocked_claims"]
    assert "erc8004_reputation_ready" in packet["still_blocked_claims"]
    assert "exact_gps_or_raw_metadata_exposure_allowed" in packet["still_blocked_claims"]


def test_claim_boundaries_stay_adjacent_and_conservative():
    packet = build_phase1_offer_card_human_operator_approval_record()
    key_order = list(packet.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert not set(packet["safe_to_claim"]) & set(packet["do_not_claim_yet"])
    assert "publication_approved" not in packet["safe_to_claim"]
    assert "customer_delivery_approved" not in packet["safe_to_claim"]
    assert "operator_publish_approval" not in packet["safe_to_claim"]


def test_write_offer_card_human_operator_approval_record_persists_valid_artifact(tmp_path):
    seed_sources(tmp_path)

    path = write_phase1_offer_card_human_operator_approval_record(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME
    assert load_phase1_offer_card_human_operator_approval_record(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_publish_approval_flip_fails_closed():
    draft = build_phase1_customer_facing_draft_packet()
    decision = build_phase1_draft_packet_operator_review_decision(draft_packet=draft)
    decision["operator_publish_approval"] = True

    with pytest.raises(CityOpsContractError, match="source decision promoted readiness"):
        build_phase1_offer_card_human_operator_approval_record(
            draft_packet=draft, review_decision=decision
        )


def test_source_draft_card_customer_ready_flip_fails_closed():
    draft = build_phase1_customer_facing_draft_packet()
    decision = build_phase1_draft_packet_operator_review_decision(draft_packet=draft)
    draft["draft_cards"][0]["draft_ready_for_customer"] = True

    with pytest.raises(CityOpsContractError, match="source draft card promoted readiness"):
        build_phase1_offer_card_human_operator_approval_record(
            draft_packet=draft, review_decision=decision
        )


def test_loader_fails_closed_on_customer_delivery_flip(tmp_path):
    packet = build_phase1_offer_card_human_operator_approval_record()
    packet["customer_delivery_approval"] = True
    (tmp_path / PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_phase1_offer_card_human_operator_approval_record(fixture_dir=tmp_path)


def test_loader_fails_closed_on_multiple_approved_offers(tmp_path):
    packet = build_phase1_offer_card_human_operator_approval_record()
    packet["approved_offer_count"] = 2
    (tmp_path / PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="exactly one offer"):
        load_phase1_offer_card_human_operator_approval_record(fixture_dir=tmp_path)


def test_loader_fails_closed_on_delivery_path_public_route_flip(tmp_path):
    packet = build_phase1_offer_card_human_operator_approval_record()
    packet["authorized_delivery_path"]["public_route_allowed"] = True
    (tmp_path / PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="delivery path drift"):
        load_phase1_offer_card_human_operator_approval_record(fixture_dir=tmp_path)


def test_source_missing_blocked_claim_fails_closed():
    draft = copy.deepcopy(build_phase1_customer_facing_draft_packet())
    decision = build_phase1_draft_packet_operator_review_decision(draft_packet=draft)
    draft["do_not_claim_yet"] = [
        claim
        for claim in draft["do_not_claim_yet"]
        if claim != "publication_approved"
    ]
    decision["do_not_claim_yet"] = [
        claim
        for claim in decision["do_not_claim_yet"]
        if claim != "publication_approved"
    ]

    with pytest.raises(CityOpsContractError, match="source missing blocked claims"):
        build_phase1_offer_card_human_operator_approval_record(
            draft_packet=draft, review_decision=decision
        )
