import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_controlled_pilot_readiness_board import (
    PHASE1_CONTROLLED_PILOT_READINESS_BOARD_FILENAME,
    PHASE1_CONTROLLED_PILOT_READINESS_BOARD_SAFE_CLAIM,
    PHASE1_CONTROLLED_PILOT_READINESS_BOARD_SCHEMA,
    build_phase1_controlled_pilot_readiness_board,
    load_phase1_controlled_pilot_readiness_board,
    write_phase1_controlled_pilot_readiness_board,
)
from mcp_server.city_ops.phase1_packet_submission_internal_package_record import (
    PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME,
    PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    build_phase1_packet_submission_internal_package_record,
)
from mcp_server.city_ops.phase1_remaining_offer_internal_package_records import (
    PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_FILENAME,
    PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_FILENAME,
    PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    build_phase1_counter_reality_check_internal_package_record,
    build_phase1_posting_compliance_internal_package_record,
)
from mcp_server.city_ops.phase1_reviewed_fixtures import (
    COUNTER_REALITY_CHECK_FIXTURE_FILENAME,
    PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME,
    PHASE1_REVIEWED_FIXTURE_REGISTRY_FILENAME,
    PHASE1_REVIEWED_FIXTURE_REGISTRY_SAFE_CLAIM,
    POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME,
    build_counter_reality_check_reviewed_fixture,
    build_packet_submission_attempt_reviewed_fixture,
    build_phase1_reviewed_fixture_registry_summary,
    build_posting_compliance_check_reviewed_fixture,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_board() -> dict:
    with (
        REVIEWED_FIXTURE_DIR / PHASE1_CONTROLLED_PILOT_READINESS_BOARD_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def seed_reviewed_outputs(tmp_path: Path) -> None:
    artifacts = {
        COUNTER_REALITY_CHECK_FIXTURE_FILENAME: build_counter_reality_check_reviewed_fixture(),
        PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME: build_packet_submission_attempt_reviewed_fixture(),
        POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME: build_posting_compliance_check_reviewed_fixture(),
    }
    registry = build_phase1_reviewed_fixture_registry_summary(
        fixtures=list(artifacts.values())
    )
    counter_record = build_phase1_counter_reality_check_internal_package_record(
        reviewed_fixture=artifacts[COUNTER_REALITY_CHECK_FIXTURE_FILENAME]
    )
    packet_record = build_phase1_packet_submission_internal_package_record(
        reviewed_fixture=artifacts[PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME]
    )
    posting_record = build_phase1_posting_compliance_internal_package_record(
        reviewed_fixture=artifacts[POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME]
    )
    artifacts[PHASE1_REVIEWED_FIXTURE_REGISTRY_FILENAME] = registry
    artifacts[PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_FILENAME] = counter_record
    artifacts[PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME] = packet_record
    artifacts[PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_FILENAME] = posting_record
    for filename, payload in artifacts.items():
        (tmp_path / filename).write_text(json.dumps(payload), encoding="utf-8")


def test_controlled_pilot_readiness_board_matches_persisted_artifact():
    board = build_phase1_controlled_pilot_readiness_board()

    assert board == read_board()
    assert load_phase1_controlled_pilot_readiness_board() == board
    assert board["schema"] == PHASE1_CONTROLLED_PILOT_READINESS_BOARD_SCHEMA
    assert board["scope"] == "internal_operator_packaging_gate_only"
    assert board["offer_order"] == [
        "counter_reality_check",
        "packet_submission_attempt",
        "posting_compliance_check",
    ]
    assert PHASE1_CONTROLLED_PILOT_READINESS_BOARD_SAFE_CLAIM in board["safe_to_claim"]
    assert PHASE1_REVIEWED_FIXTURE_REGISTRY_SAFE_CLAIM in board["safe_to_claim"]
    assert PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in board[
        "safe_to_claim"
    ]
    assert PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in board[
        "safe_to_claim"
    ]
    assert PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in board[
        "safe_to_claim"
    ]


def test_board_is_a_gate_not_customer_or_pilot_authorization():
    board = build_phase1_controlled_pilot_readiness_board()

    assert board["global_readiness"] == {
        "all_phase1_offers_have_reviewed_fixture": True,
        "all_phase1_offers_have_internal_package_record": True,
        "customer_copy_ready": False,
        "customer_visible_catalog_ready": False,
        "public_service_catalog_ready": False,
        "customer_pilot_exposure_allowed": False,
        "front_door_sku_ready": False,
        "live_acontext_ready": False,
        "runtime_parity_proven": False,
        "autonomous_dispatch_ready": False,
        "reputation_ready": False,
        "worker_copyable_doctrine_ready": False,
        "exact_gps_or_raw_metadata_exposure_allowed": False,
    }
    assert "controlled_concierge_pilot_ready" in board["do_not_claim_yet"]
    assert "customer_pilot_exposure_ready" in board["do_not_claim_yet"]
    assert "live_acontext_ready" in board["do_not_claim_yet"]
    assert "autonomous_dispatch_ready" in board["do_not_claim_yet"]
    assert "exact_gps_or_raw_metadata_exposure_allowed" in board["do_not_claim_yet"]


def test_board_rows_preserve_offer_specific_next_steps():
    board = build_phase1_controlled_pilot_readiness_board()
    rows = {row["offer"]: row for row in board["offers"]}

    assert rows["counter_reality_check"]["pilot_readiness_status"] == (
        "internal_package_recorded_not_customer_ready"
    )
    assert rows["packet_submission_attempt"]["pilot_readiness_status"] == (
        "internal_package_recorded_not_customer_ready"
    )
    assert rows["posting_compliance_check"]["pilot_readiness_status"] == (
        "internal_package_recorded_not_customer_ready"
    )
    assert rows["packet_submission_attempt"]["internal_package_record_exists"] is True
    assert rows["counter_reality_check"]["internal_package_record_exists"] is True
    assert rows["posting_compliance_check"]["internal_package_record_exists"] is True
    for row in rows.values():
        assert row["reviewed_fixture_exists"] is True
        assert row["customer_output_schema_reviewed"] is False
        assert row["customer_pilot_exposure_allowed"] is False
        assert "customer_output_schema_review" in row["blocking_gates"]
        assert "gps_and_raw_metadata_privacy_review" in row["blocking_gates"]


def test_write_controlled_pilot_readiness_board_persists_valid_artifact(tmp_path):
    seed_reviewed_outputs(tmp_path)

    path = write_phase1_controlled_pilot_readiness_board(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_CONTROLLED_PILOT_READINESS_BOARD_FILENAME
    assert load_phase1_controlled_pilot_readiness_board(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_board_fails_closed_on_missing_offer_from_registry():
    registry = copy.deepcopy(build_phase1_reviewed_fixture_registry_summary())
    registry["coverage_by_offer"].pop("posting_compliance_check")

    with pytest.raises(CityOpsContractError, match="missing source offers"):
        build_phase1_controlled_pilot_readiness_board(registry=registry)


def test_board_fails_closed_on_package_readiness_promotion():
    packet_record = copy.deepcopy(build_phase1_packet_submission_internal_package_record())
    packet_record["live_acontext_ready"] = True

    with pytest.raises(CityOpsContractError, match="package readiness drift"):
        build_phase1_controlled_pilot_readiness_board(packet_package_record=packet_record)


def test_board_loader_fails_closed_on_pilot_exposure_flip(tmp_path):
    board = build_phase1_controlled_pilot_readiness_board()
    board["global_readiness"]["customer_pilot_exposure_allowed"] = True
    (tmp_path / PHASE1_CONTROLLED_PILOT_READINESS_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_phase1_controlled_pilot_readiness_board(fixture_dir=tmp_path)


def test_board_loader_fails_closed_on_row_pilot_exposure_flip(tmp_path):
    board = build_phase1_controlled_pilot_readiness_board()
    board["offers"][0]["customer_pilot_exposure_allowed"] = True
    (tmp_path / PHASE1_CONTROLLED_PILOT_READINESS_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="overclaims pilot exposure"):
        load_phase1_controlled_pilot_readiness_board(fixture_dir=tmp_path)


def test_board_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    board = build_phase1_controlled_pilot_readiness_board()
    board["safe_to_claim"].append("customer_copy_ready")
    (tmp_path / PHASE1_CONTROLLED_PILOT_READINESS_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_phase1_controlled_pilot_readiness_board(fixture_dir=tmp_path)


def test_board_loader_fails_closed_on_dropped_blocked_claim(tmp_path):
    board = build_phase1_controlled_pilot_readiness_board()
    board["do_not_claim_yet"] = [
        claim
        for claim in board["do_not_claim_yet"]
        if claim != "worker_copyable_doctrine_ready"
    ]
    (tmp_path / PHASE1_CONTROLLED_PILOT_READINESS_BOARD_FILENAME).write_text(
        json.dumps(board), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="missing blocked claims"):
        load_phase1_controlled_pilot_readiness_board(fixture_dir=tmp_path)
