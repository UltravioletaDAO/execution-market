from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.retail_reality_human_operator_approval_request import (
    RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    build_retail_reality_human_operator_approval_request,
)
from mcp_server.city_ops.retail_reality_pending_approval_status_card import (
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME,
    build_retail_reality_pending_approval_status_card,
)
from mcp_server.city_ops.retail_reality_product_exposure_boundary_packet import (
    PACKET_BLOCKED_CLAIMS,
    PACKET_FALSE_FLAGS,
    PACKET_ID,
    RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME,
    RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM,
    RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SCHEMA,
    build_retail_reality_product_exposure_boundary_packet,
    load_retail_reality_product_exposure_boundary_packet,
    write_retail_reality_product_exposure_boundary_packet,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_packet() -> dict:
    with (ARTIFACT_DIR / RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    request = build_retail_reality_human_operator_approval_request()
    card = build_retail_reality_pending_approval_status_card(source_approval_request=request)
    (tmp_path / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME).write_text(
        json.dumps(card), encoding="utf-8"
    )


def iter_nested_keys(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key
            yield from iter_nested_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from iter_nested_keys(item)


def test_product_exposure_boundary_packet_matches_persisted_artifact_and_loader():
    packet = build_retail_reality_product_exposure_boundary_packet()

    assert packet == read_packet()
    assert load_retail_reality_product_exposure_boundary_packet() == packet
    assert packet["schema"] == RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SCHEMA
    assert packet["packet_id"] == PACKET_ID
    assert packet["scope"] == "internal_admin_retail_reality_product_exposure_boundary_human_review_only"
    assert packet["packet_status"] == "prepared_for_human_review_not_submitted_not_approved_not_exposed"
    assert RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_SAFE_CLAIM in packet[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_packet_selects_exactly_one_retail_reality_candidate_for_human_review():
    packet = build_retail_reality_product_exposure_boundary_packet()
    candidate = packet["aas_candidates"][0]

    assert packet["candidate_count"] == 1
    assert len(packet["aas_candidates"]) == 1
    assert candidate["candidate_key"] == "retail_reality_as_a_service"
    assert candidate["package_family_id"] == "retail_reality_as_a_service"
    assert candidate["offer_id"] == "storefront_hours_availability_check"
    assert candidate["human_review_status"] == "pending_human_review_not_approved"
    assert candidate["product_exposure_status"] == "not_exposed_internal_admin_review_only"
    assert candidate["candidate_text_values_visible"] is False
    assert candidate["authorized_delivery_path_recorded"] is False
    assert "candidate_text_values" not in set(iter_nested_keys(packet))


def test_human_review_cards_keep_boundary_digest_and_blocked_claims_adjacent():
    packet = build_retail_reality_product_exposure_boundary_packet()
    cards = packet["human_review_cards"]

    assert [card["card_id"] for card in cards] == [
        "single_candidate_boundary",
        "selected_boundary_digest_only",
        "blocked_product_exposure_claims",
        "next_separate_artifact_only",
    ]
    assert cards[0]["candidate_count"] == 1
    assert cards[0]["product_exposure_approved"] is False
    assert cards[1]["candidate_text_values_visible"] is False
    assert cards[2]["do_not_claim_yet"] == packet["claim_boundaries"]["do_not_claim_yet"]
    assert cards[3]["approval_can_be_inferred_from_this_packet"] is False
    assert cards[3]["customer_exposure_can_be_inferred_from_this_packet"] is False


def test_packet_blocks_all_customer_public_catalog_pricing_queue_dispatch_runtime_and_authority_claims():
    packet = build_retail_reality_product_exposure_boundary_packet()
    safe = set(packet["claim_boundaries"]["safe_to_claim"])
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])

    for claim in PACKET_BLOCKED_CLAIMS:
        assert claim in blocked
        assert claim not in safe
    for flag, expected in PACKET_FALSE_FLAGS.items():
        assert packet[flag] is expected
        assert packet["readiness"][flag] is expected
    for flag in [
        "public_route_registered",
        "catalog_route_registered",
        "customer_visible",
        "pricing_enabled",
        "dispatch_enabled",
        "writes_live_acontext",
        "mutates_runtime_adapter_or_session_manager",
        "emits_reputation_receipts",
        "exposes_exact_gps_or_raw_metadata",
        "exposes_private_context",
        "publishes_worker_doctrine",
    ]:
        assert packet["access_policy"][flag] is False
    assert packet["still_blocked_claims"] == packet["claim_boundaries"]["do_not_claim_yet"]


def test_write_packet_persists_valid_fixture_from_sources(tmp_path):
    seed_sources(tmp_path)

    path = write_retail_reality_product_exposure_boundary_packet(artifact_dir=tmp_path)

    assert path == tmp_path / RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME
    assert load_retail_reality_product_exposure_boundary_packet(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_packet_fails_closed_when_source_status_is_promoted():
    status_card = copy.deepcopy(build_retail_reality_pending_approval_status_card())
    status_card["source_approval_request_status"] = "approved"

    with pytest.raises(CityOpsContractError, match="source request status promoted"):
        build_retail_reality_product_exposure_boundary_packet(status_card=status_card)


def test_packet_fails_closed_when_candidate_count_changes(tmp_path):
    seed_sources(tmp_path)
    packet = build_retail_reality_product_exposure_boundary_packet(artifact_dir=tmp_path)
    packet["candidate_count"] = 2
    packet["aas_candidates"].append(copy.deepcopy(packet["aas_candidates"][0]))
    (tmp_path / RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="exactly one candidate"):
        load_retail_reality_product_exposure_boundary_packet(artifact_dir=tmp_path)


def test_loader_fails_closed_on_customer_visibility_promotion(tmp_path):
    seed_sources(tmp_path)
    packet = build_retail_reality_product_exposure_boundary_packet(artifact_dir=tmp_path)
    packet["access_policy"]["customer_visible"] = True
    (tmp_path / RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="access promoted customer_visible"):
        load_retail_reality_product_exposure_boundary_packet(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    seed_sources(tmp_path)
    packet = build_retail_reality_product_exposure_boundary_packet(artifact_dir=tmp_path)
    packet["claim_boundaries"]["safe_to_claim"].append(
        "retail_reality_product_exposure_customer_delivery_approved"
    )
    (tmp_path / RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_retail_reality_product_exposure_boundary_packet(artifact_dir=tmp_path)


def test_loader_fails_closed_on_candidate_text_value_leak(tmp_path):
    seed_sources(tmp_path)
    packet = build_retail_reality_product_exposure_boundary_packet(artifact_dir=tmp_path)
    packet["aas_candidates"][0]["candidate_text_values"] = {"summary": "leak"}
    (tmp_path / RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="candidate drift|leaked forbidden keys"):
        load_retail_reality_product_exposure_boundary_packet(artifact_dir=tmp_path)
