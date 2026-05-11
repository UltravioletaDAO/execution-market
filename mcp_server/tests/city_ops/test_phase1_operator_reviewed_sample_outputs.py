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
    build_phase1_customer_output_schema_review_gate,
)
from mcp_server.city_ops.phase1_operator_reviewed_sample_outputs import (
    PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME,
    PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SAFE_CLAIM,
    PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SCHEMA,
    build_phase1_operator_reviewed_sample_outputs,
    load_phase1_operator_reviewed_sample_outputs,
    write_phase1_operator_reviewed_sample_outputs,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_packet() -> dict:
    with (
        REVIEWED_FIXTURE_DIR / PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def seed_schema_gate(tmp_path: Path) -> None:
    gate = build_phase1_customer_output_schema_review_gate()
    (tmp_path / PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )


def test_operator_reviewed_sample_outputs_match_persisted_artifact():
    packet = build_phase1_operator_reviewed_sample_outputs()

    assert packet == read_packet()
    assert load_phase1_operator_reviewed_sample_outputs() == packet
    assert packet["schema"] == PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SCHEMA
    assert packet["scope"] == "internal_admin_sample_output_review_only"
    assert PHASE1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_SAFE_CLAIM in packet[
        "safe_to_claim"
    ]
    assert PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SAFE_CLAIM in packet[
        "safe_to_claim"
    ]


def test_samples_are_reviewed_but_not_publishable_customer_copy():
    packet = build_phase1_operator_reviewed_sample_outputs()

    assert packet["sample_review_status"] == "operator_reviewed_internal_samples_not_customer_copy"
    assert packet["customer_copy_created"] is False
    assert packet["customer_copy_ready"] is False
    assert packet["customer_visible_catalog_ready"] is False
    assert packet["public_service_catalog_ready"] is False
    assert packet["customer_pilot_exposure_allowed"] is False
    assert packet["front_door_sku_ready"] is False
    assert packet["sample_outputs_publishable"] is False
    assert packet["live_acontext_ready"] is False
    assert packet["runtime_parity_proven"] is False
    assert packet["autonomous_dispatch_ready"] is False
    assert packet["reputation_ready"] is False
    assert packet["worker_copyable_doctrine_ready"] is False
    assert packet["exact_gps_or_raw_metadata_exposure_allowed"] is False
    assert "customer_sample_publication_ready" in packet["do_not_claim_yet"]


def test_each_offer_has_only_allowed_schema_fields_and_review_flags():
    packet = build_phase1_operator_reviewed_sample_outputs()

    assert packet["offer_order"] == [
        "counter_reality_check",
        "packet_submission_attempt",
        "posting_compliance_check",
    ]
    assert packet["sample_output_fields"] == BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS
    assert packet["forbidden_customer_output_fields"] == FORBIDDEN_CUSTOMER_OUTPUT_FIELDS

    samples = {sample["offer"]: sample for sample in packet["offer_sample_outputs"]}
    assert set(samples) == set(packet["offer_order"])
    for sample in samples.values():
        assert sample["sample_review_status"] == "operator_reviewed_internal_sample_not_customer_copy"
        assert sample["sample_publishable"] is False
        assert sample["customer_copy_ready"] is False
        assert sample["customer_pilot_exposure_allowed"] is False
        assert list(sample["allowed_field_values"].keys()) == BASE_ALLOWED_CUSTOMER_OUTPUT_FIELDS
        assert sample["forbidden_fields_absent"] == FORBIDDEN_CUSTOMER_OUTPUT_FIELDS
        assert sample["separate_reviews"]["privacy_boundary_review_passed"] is True
        assert sample["separate_reviews"]["legal_advice_exclusion_review_passed"] is True
        assert sample["separate_reviews"]["non_guarantee_language_review_passed"] is True
        assert sample["separate_reviews"]["operator_publish_approval"] is False
        assert sample["separate_reviews"]["customer_delivery_approval"] is False

    assert "coordinates" in samples["posting_compliance_check"]["allowed_field_values"][
        "reviewed_evidence_summary"
    ]
    assert "without coordinates" in samples["posting_compliance_check"][
        "allowed_field_values"
    ]["reviewed_evidence_summary"]


def test_claim_boundaries_stay_adjacent_and_conservative():
    packet = build_phase1_operator_reviewed_sample_outputs()
    key_order = list(packet.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert not set(packet["safe_to_claim"]) & set(packet["do_not_claim_yet"])
    assert "customer_copy_ready" in packet["do_not_claim_yet"]
    assert "public_service_catalog_ready" in packet["do_not_claim_yet"]
    assert "dispatch_routing_ready" in packet["do_not_claim_yet"]
    assert "erc8004_reputation_ready" in packet["do_not_claim_yet"]
    assert "exact_gps_or_raw_metadata_exposure_allowed" in packet["do_not_claim_yet"]


def test_write_operator_reviewed_sample_outputs_persists_valid_artifact(tmp_path):
    seed_schema_gate(tmp_path)

    path = write_phase1_operator_reviewed_sample_outputs(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME
    assert load_phase1_operator_reviewed_sample_outputs(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_gate_readiness_promotion_fails_closed():
    gate = build_phase1_customer_output_schema_review_gate()
    gate["customer_copy_ready"] = True

    with pytest.raises(CityOpsContractError, match="source gate promoted readiness"):
        build_phase1_operator_reviewed_sample_outputs(schema_gate=gate)


def test_loader_fails_closed_on_sample_publishable_flip(tmp_path):
    packet = build_phase1_operator_reviewed_sample_outputs()
    packet["offer_sample_outputs"][0]["sample_publishable"] = True
    (tmp_path / PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="sample promoted readiness"):
        load_phase1_operator_reviewed_sample_outputs(fixture_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    packet = build_phase1_operator_reviewed_sample_outputs()
    packet["safe_to_claim"].append("customer_sample_publication_ready")
    (tmp_path / PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_phase1_operator_reviewed_sample_outputs(fixture_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_customer_field(tmp_path):
    packet = build_phase1_operator_reviewed_sample_outputs()
    values = packet["offer_sample_outputs"][2]["allowed_field_values"]
    values["exact_gps_coordinates"] = "blocked"
    (tmp_path / PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="allowed field drift"):
        load_phase1_operator_reviewed_sample_outputs(fixture_dir=tmp_path)


def test_loader_fails_closed_on_missing_review_gate(tmp_path):
    packet = build_phase1_operator_reviewed_sample_outputs()
    packet["offer_sample_outputs"][1]["separate_reviews"][
        "non_guarantee_language_review_passed"
    ] = False
    (tmp_path / PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="missing review gates"):
        load_phase1_operator_reviewed_sample_outputs(fixture_dir=tmp_path)


def test_source_gate_missing_blocked_claim_fails_closed():
    gate = copy.deepcopy(build_phase1_customer_output_schema_review_gate())
    gate["do_not_claim_yet"] = [
        claim
        for claim in gate["do_not_claim_yet"]
        if claim != "customer_copy_ready"
    ]

    with pytest.raises(CityOpsContractError, match="source missing blocked claims"):
        build_phase1_operator_reviewed_sample_outputs(schema_gate=gate)
