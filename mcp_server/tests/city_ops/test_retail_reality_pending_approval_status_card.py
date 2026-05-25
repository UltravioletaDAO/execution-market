import copy
import hashlib
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.retail_reality_human_operator_approval_request import (
    APPROVAL_REQUEST_STATUS,
    REQUEST_BLOCKED_CLAIMS,
    RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
    build_retail_reality_human_operator_approval_request,
)
from mcp_server.city_ops.retail_reality_pending_approval_status_card import (
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME,
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM,
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SCHEMA,
    STATUS_CARD_BLOCKED_CLAIMS,
    STATUS_CARD_FALSE_FLAGS,
    STATUS_CARD_ID,
    build_retail_reality_pending_approval_status_card,
    load_retail_reality_pending_approval_status_card,
    write_retail_reality_pending_approval_status_card,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_status_card() -> dict:
    with (ARTIFACT_DIR / RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def iter_nested_keys(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key
            yield from iter_nested_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from iter_nested_keys(item)


def test_pending_approval_status_card_matches_persisted_artifact():
    card = build_retail_reality_pending_approval_status_card()

    assert card == read_status_card()
    assert load_retail_reality_pending_approval_status_card() == card
    assert card["schema"] == RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SCHEMA
    assert card["status_card_id"] == STATUS_CARD_ID
    assert card["scope"] == "internal_admin_retail_reality_pending_approval_status_card_only"
    assert RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM in card["safe_to_claim"]
    assert RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM in card["safe_to_claim"]


def test_status_card_advances_ladder_without_recording_approval_or_customer_readiness():
    card = build_retail_reality_pending_approval_status_card()

    assert card["ladder_boundary"]["covered_steps"][-1] == "pending_approval_status_card"
    assert card["ladder_boundary"]["promotion_allowed"] is False
    assert card["source_approval_request_status"] == APPROVAL_REQUEST_STATUS
    assert card["access_policy"]["surface"] == "internal_admin_only"
    assert card["access_policy"]["public_route_registered"] is False
    assert card["access_policy"]["customer_visible"] is False
    assert card["access_policy"]["dispatch_enabled"] is False
    assert card["access_policy"]["exposes_exact_gps_or_raw_metadata"] is False
    assert card["access_policy"]["exposes_private_context"] is False
    assert card["access_policy"]["private_context_release_allowed"] is False
    assert card["human_operator_approval_recorded"] is False
    assert card["selected_text_boundary_approved"] is False
    assert card["customer_copy_ready"] is False
    assert card["publication_approved"] is False
    assert all(card["readiness"][flag] is False for flag in STATUS_CARD_FALSE_FLAGS)


def test_status_queue_item_is_digest_bound_and_hides_candidate_text_values():
    request = build_retail_reality_human_operator_approval_request()
    card = build_retail_reality_pending_approval_status_card(source_approval_request=request)
    queue_item = card["status_queue_items"][0]
    boundary = request["selected_text_boundary"]

    assert card["status_queue_item_count"] == 1
    assert queue_item["request_id"] == request["request_id"]
    assert queue_item["source_request_digest_sha256"] == digest(request)
    assert card["source_approval_request_digest_sha256"] == digest(request)
    assert queue_item["selected_text_boundary_key"] == boundary["key"]
    assert queue_item["selected_text_boundary_digest_sha256"] == boundary[
        "candidate_text_digest_sha256"
    ]
    assert queue_item["candidate_text_field_names"] == boundary["candidate_text_fields"]
    assert queue_item["candidate_text_values_visible"] is False
    assert "candidate_text_values" not in queue_item
    assert "candidate_text_values" not in set(iter_nested_keys(card))

    selected_boundary_card = card["display_cards"][1]
    assert selected_boundary_card["card_id"] == "selected_boundary_digest"
    assert selected_boundary_card["boundary_digest_sha256"] == boundary[
        "candidate_text_digest_sha256"
    ]
    assert selected_boundary_card["candidate_text_values_visible"] is False
    assert "candidate_text_values" not in selected_boundary_card


def test_status_card_keeps_required_reviews_pending_and_claims_adjacent():
    card = build_retail_reality_pending_approval_status_card()
    queue_item = card["status_queue_items"][0]
    review_card = card["display_cards"][2]
    blocked_card = card["display_cards"][3]

    assert queue_item["pre_approval_checks_passed_here"] == 0
    assert queue_item["redaction_and_authority_requirements_passed_here"] == 0
    assert queue_item["authorized_delivery_path_recorded"] is False
    assert review_card["pre_approval_checks_passed_here"] == 0
    assert review_card["redaction_and_authority_requirements_passed_here"] == 0
    assert blocked_card["safe_to_claim"] == card["source_safe_claims_inherited"] or (
        RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM in blocked_card["safe_to_claim"]
    )
    assert blocked_card["do_not_claim_yet"]
    assert card["derived_output_contract"]["safe_and_blocked_claims_remain_adjacent"] is True
    assert card["derived_output_contract"]["source_candidate_text_values_hidden"] is True


def test_status_card_blocks_customer_public_dispatch_reputation_runtime_and_retail_overclaims():
    card = build_retail_reality_pending_approval_status_card()
    blocked = set(card["do_not_claim_yet"])

    for claim in REQUEST_BLOCKED_CLAIMS + STATUS_CARD_BLOCKED_CLAIMS:
        assert claim in blocked
        assert claim not in card["safe_to_claim"]
    for claim in [
        "retail_reality_pending_status_card_customer_copy_ready",
        "retail_reality_pending_status_card_customer_delivery_ready",
        "retail_reality_pending_status_card_public_route_ready",
        "retail_reality_pending_status_card_dispatch_ready",
        "retail_reality_pending_status_card_reputation_ready",
        "retail_reality_pending_status_card_live_runtime_ready",
        "retail_reality_pending_status_card_retail_authority_ready",
        "retail_reality_pending_status_card_worker_copyable_retail_doctrine_ready",
    ]:
        assert claim in blocked
        assert claim not in card["safe_to_claim"]
    assert card["still_blocked_claims"] == card["do_not_claim_yet"]


def test_write_retail_reality_pending_approval_status_card_persists_valid_artifact(tmp_path):
    path = write_retail_reality_pending_approval_status_card(artifact_dir=tmp_path)

    assert path == tmp_path / RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME
    assert load_retail_reality_pending_approval_status_card(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_status_card_fails_closed_when_source_request_status_is_promoted():
    request = copy.deepcopy(build_retail_reality_human_operator_approval_request())
    request["approval_request_status"] = "approved"

    with pytest.raises(CityOpsContractError, match="source request status promoted"):
        build_retail_reality_pending_approval_status_card(source_approval_request=request)


def test_status_card_fails_closed_when_source_boundary_is_promoted():
    request = copy.deepcopy(build_retail_reality_human_operator_approval_request())
    request["selected_text_boundary"]["customer_delivery_authorized_by_boundary"] = True

    with pytest.raises(CityOpsContractError, match="source boundary promoted"):
        build_retail_reality_pending_approval_status_card(source_approval_request=request)


def test_loader_fails_closed_on_public_access_promotion(tmp_path):
    request = build_retail_reality_human_operator_approval_request()
    card = build_retail_reality_pending_approval_status_card(source_approval_request=request)
    card["access_policy"]["public_route_registered"] = True
    (tmp_path / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME).write_text(
        json.dumps(card), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="access promoted public_route_registered"):
        load_retail_reality_pending_approval_status_card(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    request = build_retail_reality_human_operator_approval_request()
    card = build_retail_reality_pending_approval_status_card(source_approval_request=request)
    card["safe_to_claim"].append("retail_reality_pending_status_card_customer_copy_ready")
    (tmp_path / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME).write_text(
        json.dumps(card), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_retail_reality_pending_approval_status_card(artifact_dir=tmp_path)


def test_loader_fails_closed_on_candidate_text_value_leak(tmp_path):
    request = build_retail_reality_human_operator_approval_request()
    card = build_retail_reality_pending_approval_status_card(source_approval_request=request)
    card["status_queue_items"][0]["candidate_text_values"] = request["selected_text_boundary"][
        "candidate_text_values"
    ]
    (tmp_path / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME).write_text(
        json.dumps(card), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="candidate text leaked"):
        load_retail_reality_pending_approval_status_card(artifact_dir=tmp_path)
