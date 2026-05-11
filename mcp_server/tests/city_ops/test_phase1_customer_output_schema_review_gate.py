import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_customer_output_schema_review_gate import (
    BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS,
    FORBIDDEN_CUSTOMER_OUTPUT_FIELDS,
    PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_FILENAME,
    PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SAFE_CLAIM,
    PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SCHEMA,
    build_phase1_customer_output_schema_review_gate,
    load_phase1_customer_output_schema_review_gate,
    write_phase1_customer_output_schema_review_gate,
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

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_gate() -> dict:
    with (
        REVIEWED_FIXTURE_DIR / PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def seed_package_records(tmp_path: Path) -> None:
    artifacts = {
        PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_FILENAME: build_phase1_counter_reality_check_internal_package_record(),
        PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME: build_phase1_packet_submission_internal_package_record(),
        PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_FILENAME: build_phase1_posting_compliance_internal_package_record(),
    }
    for filename, payload in artifacts.items():
        (tmp_path / filename).write_text(json.dumps(payload), encoding="utf-8")


def test_customer_output_schema_review_gate_matches_persisted_artifact():
    gate = build_phase1_customer_output_schema_review_gate()

    assert gate == read_gate()
    assert load_phase1_customer_output_schema_review_gate() == gate
    assert gate["schema"] == PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SCHEMA
    assert gate["scope"] == "internal_admin_schema_review_only"
    assert PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SAFE_CLAIM in gate["safe_to_claim"]
    assert PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in gate[
        "safe_to_claim"
    ]
    assert PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in gate[
        "safe_to_claim"
    ]
    assert PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in gate[
        "safe_to_claim"
    ]


def test_gate_is_schema_only_not_customer_or_pilot_authorization():
    gate = build_phase1_customer_output_schema_review_gate()

    assert gate["schema_review_status"] == "reviewed_for_future_customer_output_shape_not_copy"
    assert gate["customer_output_schema_review_gate_complete"] is True
    assert gate["customer_copy_created"] is False
    assert gate["customer_copy_ready"] is False
    assert gate["customer_visible_catalog_ready"] is False
    assert gate["public_service_catalog_ready"] is False
    assert gate["customer_pilot_exposure_allowed"] is False
    assert gate["front_door_sku_ready"] is False
    assert gate["live_acontext_ready"] is False
    assert gate["runtime_parity_proven"] is False
    assert gate["autonomous_dispatch_ready"] is False
    assert gate["reputation_ready"] is False
    assert gate["worker_copyable_doctrine_ready"] is False
    assert gate["exact_gps_or_raw_metadata_exposure_allowed"] is False
    assert "controlled_concierge_pilot_ready" in gate["do_not_claim_yet"]
    assert "customer_pilot_exposure_ready" in gate["do_not_claim_yet"]
    assert "exact_gps_or_raw_metadata_exposure_allowed" in gate["do_not_claim_yet"]


def test_gate_reviews_all_three_offer_schemas_without_copy():
    gate = build_phase1_customer_output_schema_review_gate()

    assert gate["offer_order"] == [
        "counter_reality_check",
        "packet_submission_attempt",
        "posting_compliance_check",
    ]
    reviews = {review["offer"]: review for review in gate["offer_schema_reviews"]}
    assert set(reviews) == set(gate["offer_order"])
    for review in reviews.values():
        assert review["schema_review_status"] == "schema_shape_reviewed_not_customer_copy"
        assert review["customer_output_schema_review_gate_complete"] is True
        assert review["customer_copy_created"] is False
        assert review["customer_copy_ready"] is False
        assert review["customer_pilot_exposure_allowed"] is False
        assert review["allowed_customer_output_fields"] == BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS
        assert review["forbidden_customer_output_fields"] == FORBIDDEN_CUSTOMER_OUTPUT_FIELDS
        assert review["required_disclaimer"]
        assert review["privacy_note"]
        assert review["next_gate"]
    assert "Exact GPS" in reviews["posting_compliance_check"]["privacy_note"]


def test_gate_keeps_allowed_and_forbidden_fields_adjacent_to_claim_boundaries():
    gate = build_phase1_customer_output_schema_review_gate()
    key_order = list(gate.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert not set(gate["safe_to_claim"]) & set(gate["do_not_claim_yet"])
    assert not set(gate["shared_allowed_customer_output_fields"]) & set(
        gate["shared_forbidden_customer_output_fields"]
    )
    assert "reviewed_evidence_summary" in gate["shared_allowed_customer_output_fields"]
    assert "exact_gps_coordinates" in gate["shared_forbidden_customer_output_fields"]
    assert "legal_advice_or_legal_sufficiency" in gate[
        "shared_forbidden_customer_output_fields"
    ]


def test_write_customer_output_schema_review_gate_persists_valid_artifact(tmp_path):
    seed_package_records(tmp_path)

    path = write_phase1_customer_output_schema_review_gate(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_FILENAME
    assert load_phase1_customer_output_schema_review_gate(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_gate_fails_closed_on_source_package_readiness_promotion():
    packet_record = copy.deepcopy(build_phase1_packet_submission_internal_package_record())
    packet_record["runtime_parity_proven"] = True

    with pytest.raises(CityOpsContractError, match="package readiness drift"):
        build_phase1_customer_output_schema_review_gate(
            packet_package_record=packet_record
        )


def test_gate_fails_closed_on_source_package_missing_blocked_claim():
    counter_record = copy.deepcopy(build_phase1_counter_reality_check_internal_package_record())
    counter_record["do_not_claim_yet"] = [
        claim
        for claim in counter_record["do_not_claim_yet"]
        if claim != "customer_copy_ready"
    ]

    with pytest.raises(CityOpsContractError, match="missing blocked claims"):
        build_phase1_customer_output_schema_review_gate(
            counter_package_record=counter_record
        )


def test_gate_loader_fails_closed_on_customer_copy_flip(tmp_path):
    gate = build_phase1_customer_output_schema_review_gate()
    gate["customer_copy_ready"] = True
    (tmp_path / PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_phase1_customer_output_schema_review_gate(fixture_dir=tmp_path)


def test_gate_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    gate = build_phase1_customer_output_schema_review_gate()
    gate["safe_to_claim"].append("customer_visible_catalog_ready")
    (tmp_path / PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_phase1_customer_output_schema_review_gate(fixture_dir=tmp_path)


def test_gate_loader_fails_closed_on_allowed_exact_gps_field(tmp_path):
    gate = build_phase1_customer_output_schema_review_gate()
    gate["shared_allowed_customer_output_fields"].append("exact_gps_coordinates")
    gate["offer_schema_reviews"][0]["allowed_customer_output_fields"].append(
        "exact_gps_coordinates"
    )
    (tmp_path / PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="allowed field drift"):
        load_phase1_customer_output_schema_review_gate(fixture_dir=tmp_path)


def test_gate_loader_fails_closed_on_offer_copy_creation(tmp_path):
    gate = build_phase1_customer_output_schema_review_gate()
    gate["offer_schema_reviews"][1]["customer_copy_created"] = True
    (tmp_path / PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="offer promoted readiness"):
        load_phase1_customer_output_schema_review_gate(fixture_dir=tmp_path)
