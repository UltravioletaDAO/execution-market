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
    RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME,
    build_retail_reality_product_exposure_boundary_packet,
)
from mcp_server.city_ops.retail_reality_product_exposure_hold_regression_guard import (
    GUARD_BLOCKED_CLAIMS,
    GUARD_FALSE_FLAGS,
    GUARD_ID,
    GUARD_STATUS,
    NEXT_ALLOWED_MOVE,
    RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME,
    RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM,
    RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SCHEMA,
    build_retail_reality_product_exposure_hold_regression_guard,
    load_retail_reality_product_exposure_hold_regression_guard,
    write_retail_reality_product_exposure_hold_regression_guard,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_guard() -> dict:
    with (ARTIFACT_DIR / RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    request = build_retail_reality_human_operator_approval_request()
    card = build_retail_reality_pending_approval_status_card(source_approval_request=request)
    packet = build_retail_reality_product_exposure_boundary_packet(status_card=card)
    (tmp_path / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_FILENAME).write_text(
        json.dumps(card), encoding="utf-8"
    )
    (tmp_path / RETAIL_REALITY_PRODUCT_EXPOSURE_BOUNDARY_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )


def test_hold_regression_guard_matches_persisted_artifact_and_loader():
    guard = build_retail_reality_product_exposure_hold_regression_guard()

    assert guard == read_guard()
    assert load_retail_reality_product_exposure_hold_regression_guard() == guard
    assert guard["schema"] == RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SCHEMA
    assert guard["guard_id"] == GUARD_ID
    assert guard["guard_status"] == GUARD_STATUS
    assert RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_SAFE_CLAIM in guard[
        "safe_to_claim"
    ]


def test_guard_keeps_no_human_answer_default_and_one_candidate_boundary_digest():
    guard = build_retail_reality_product_exposure_hold_regression_guard()

    assert guard["candidate_count"] == 1
    assert guard["candidate_key"] == "retail_reality_as_a_service"
    assert guard["candidate_text_values_visible"] is False
    assert guard["source_selected_boundary_digest_sha256"]
    assert guard["next_allowed_move"] == NEXT_ALLOWED_MOVE
    assert guard["no_human_answer_default"] == "keep_all_product_forks_internal_admin_only"


def test_guard_regresses_all_customer_public_dispatch_runtime_reputation_and_authority_claims():
    guard = build_retail_reality_product_exposure_hold_regression_guard()
    safe = set(guard["safe_to_claim"])
    blocked = set(guard["do_not_claim_yet"])

    for claim in [*PACKET_BLOCKED_CLAIMS, *GUARD_BLOCKED_CLAIMS]:
        assert claim in blocked
        assert claim not in safe
    for flag, expected in GUARD_FALSE_FLAGS.items():
        assert guard["readiness"][flag] is expected
        assert guard["regression_assertions"][flag] is expected
    assert guard["still_blocked_claims"] == guard["do_not_claim_yet"]


def test_write_guard_persists_valid_fixture_from_sources(tmp_path):
    seed_sources(tmp_path)

    path = write_retail_reality_product_exposure_hold_regression_guard(artifact_dir=tmp_path)

    assert path == tmp_path / RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME
    assert load_retail_reality_product_exposure_hold_regression_guard(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_guard_fails_closed_when_source_packet_is_promoted_to_answered():
    packet = copy.deepcopy(build_retail_reality_product_exposure_boundary_packet())
    packet["human_operator_answer_recorded"] = True

    with pytest.raises(CityOpsContractError, match="source promoted flag human_operator_answer_recorded"):
        build_retail_reality_product_exposure_hold_regression_guard(source_packet=packet)


def test_guard_fails_closed_when_source_packet_safe_claim_promotes_customer_delivery():
    packet = copy.deepcopy(build_retail_reality_product_exposure_boundary_packet())
    packet["claim_boundaries"]["safe_to_claim"].append(
        "retail_reality_product_exposure_customer_delivery_approved"
    )

    with pytest.raises(CityOpsContractError, match="source forbidden safe claims"):
        build_retail_reality_product_exposure_hold_regression_guard(source_packet=packet)


def test_guard_fails_closed_when_source_packet_leaks_candidate_text_values():
    packet = copy.deepcopy(build_retail_reality_product_exposure_boundary_packet())
    packet["aas_candidates"][0]["candidate_text_values"] = {"summary": "leak"}

    with pytest.raises(CityOpsContractError, match="leaked forbidden keys"):
        build_retail_reality_product_exposure_hold_regression_guard(source_packet=packet)


def test_loader_fails_closed_on_guard_readiness_promotion(tmp_path):
    seed_sources(tmp_path)
    guard = build_retail_reality_product_exposure_hold_regression_guard(artifact_dir=tmp_path)
    guard["readiness"]["dispatch_ready"] = True
    (tmp_path / RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME).write_text(
        json.dumps(guard), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="readiness promoted dispatch_ready"):
        load_retail_reality_product_exposure_hold_regression_guard(artifact_dir=tmp_path)


def test_loader_fails_closed_on_guard_forbidden_safe_claim(tmp_path):
    seed_sources(tmp_path)
    guard = build_retail_reality_product_exposure_hold_regression_guard(artifact_dir=tmp_path)
    guard["safe_to_claim"].append("customer_delivery_approved")
    (tmp_path / RETAIL_REALITY_PRODUCT_EXPOSURE_HOLD_REGRESSION_GUARD_FILENAME).write_text(
        json.dumps(guard), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_retail_reality_product_exposure_hold_regression_guard(artifact_dir=tmp_path)
