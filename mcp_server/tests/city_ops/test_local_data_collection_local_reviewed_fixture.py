import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.local_data_collection_fixture_review_gate import (
    LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    build_local_data_collection_fixture_review_gate,
)
from mcp_server.city_ops.local_data_collection_local_reviewed_fixture import (
    COVERED_LADDER_STEPS,
    FIXTURE_ID,
    LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_FILENAME,
    LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
    LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_SCHEMA,
    LOCAL_FIXTURE_REVIEW_CHECKS,
    NEXT_REQUIRED_LADDER_STEPS,
    build_local_data_collection_local_reviewed_fixture,
    load_local_data_collection_local_reviewed_fixture,
    write_local_data_collection_local_reviewed_fixture,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture() -> dict:
    with (ARTIFACT_DIR / LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_local_data_collection_local_reviewed_fixture_matches_persisted_artifact():
    fixture = build_local_data_collection_local_reviewed_fixture()

    assert fixture == read_fixture()
    assert load_local_data_collection_local_reviewed_fixture() == fixture
    assert fixture["schema"] == LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_SCHEMA
    assert fixture["fixture_id"] == FIXTURE_ID
    assert fixture["scope"] == "internal_admin_local_data_collection_local_reviewed_fixture_only"
    assert fixture["offer_id"] == "one_window_count_or_measurement_snapshot"
    assert LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM in fixture["safe_to_claim"]
    assert LOCAL_DATA_COLLECTION_FIXTURE_REVIEW_GATE_SAFE_CLAIM in fixture["safe_to_claim"]
    assert AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM in fixture["safe_to_claim"]


def test_fixture_advances_exactly_one_ladder_rung_without_promotion():
    fixture = build_local_data_collection_local_reviewed_fixture()

    assert fixture["ladder_boundary"]["covered_steps"] == COVERED_LADDER_STEPS
    assert fixture["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert fixture["ladder_boundary"]["promotion_allowed"] is False
    assert fixture["local_fixture"]["review_status"] == (
        "reviewed_internal_fixture_only_not_promoted"
    )


def test_fixture_populates_required_count_measurement_evidence_and_output_fields():
    fixture = build_local_data_collection_local_reviewed_fixture()
    local_fixture = fixture["local_fixture"]
    evidence = local_fixture["evidence_contract_snapshot"]
    reviewed_output = local_fixture["reviewed_output"]

    for field in [
        "single_place_or_context_reference_without_exact_public_coordinates",
        "single_observation_window",
        "single_count_or_measurement_question",
        "allowed_observation_method",
        "visible_context_photo_or_permitted_visual_snapshot",
        "raw_count_or_measurement_value_with_units_where_applicable",
        "method_note_and_uncertainty_range",
        "ambiguity_or_occlusion_note",
        "what_was_not_checked",
    ]:
        assert field in evidence

    for field in local_fixture["reviewed_output_schema"]["required_fields"]:
        assert field in reviewed_output
    assert "not a representative dataset" in reviewed_output[
        "plain_language_observation_status"
    ]
    assert "not continuous monitoring" in reviewed_output[
        "plain_language_observation_status"
    ]
    assert "count_range_7_to_9" in evidence[
        "raw_count_or_measurement_value_with_units_where_applicable"
    ]
    assert "+/-1 uncertainty" in reviewed_output["method_summary"]
    assert "does not infer averages" in reviewed_output["uncertainty_and_ambiguity_summary"]


def test_fixture_blocks_customer_dataset_analytics_dispatch_reputation_and_worker_doctrine():
    fixture = build_local_data_collection_local_reviewed_fixture()
    local_fixture = fixture["local_fixture"]

    assert local_fixture["customer_copy_changed"] is False
    assert local_fixture["customer_delivery_allowed"] is False
    assert local_fixture["publication_allowed"] is False
    assert local_fixture["catalog_allowed"] is False
    assert local_fixture["dataset_publication_allowed"] is False
    assert local_fixture["analytics_publication_allowed"] is False
    assert local_fixture["pricing_quote_allowed"] is False
    assert local_fixture["dispatch_allowed"] is False
    assert local_fixture["reputation_attachment_allowed"] is False
    assert local_fixture["live_runtime_write_allowed"] is False
    assert local_fixture["worker_skill_dna_allowed"] is False
    assert local_fixture["worker_copyable_doctrine_allowed"] is False
    assert local_fixture["statistical_representativeness_claim_allowed"] is False
    assert local_fixture["continuous_monitoring_claim_allowed"] is False
    assert local_fixture["official_dataset_certification_allowed"] is False
    assert local_fixture["exactness_beyond_method_allowed"] is False
    assert local_fixture["predictive_analytics_allowed"] is False

    for claim in [
        "customer_copy_ready",
        "public_service_catalog_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_copyable_data_collection_doctrine",
        "statistical_representativeness",
        "continuous_monitoring",
        "official_dataset_certification",
        "exactness_beyond_observed_method",
        "predictive_analytics",
        "public_dataset_ready",
        "local_data_collection_local_fixture_dataset_ready",
        "local_data_collection_local_fixture_analytics_ready",
        "local_data_collection_local_fixture_dispatch_ready",
        "local_data_collection_local_fixture_worker_doctrine_ready",
    ]:
        assert claim in fixture["do_not_claim_yet"]
        assert claim not in fixture["safe_to_claim"]


def test_readiness_flags_remain_false():
    fixture = build_local_data_collection_local_reviewed_fixture()

    assert fixture["readiness"]["customer_copy_ready"] is False
    assert fixture["readiness"]["public_service_catalog_ready"] is False
    assert fixture["readiness"]["live_acontext_ready"] is False
    assert fixture["readiness"]["runtime_parity_proven"] is False
    assert fixture["readiness"]["autonomous_dispatch_ready"] is False
    assert fixture["readiness"]["reputation_ready"] is False
    assert fixture["readiness"]["worker_skill_dna_ready"] is False
    assert fixture["readiness"]["worker_copyable_doctrine_ready"] is False
    assert fixture["readiness"]["exact_gps_or_raw_metadata_exposure_allowed"] is False


def test_local_review_checks_pass_only_for_local_fixture_and_still_block_promotion():
    fixture = build_local_data_collection_local_reviewed_fixture()

    assert [item["check_id"] for item in fixture["local_review_checks"]] == (
        LOCAL_FIXTURE_REVIEW_CHECKS
    )
    for item in fixture["local_review_checks"]:
        assert item["status"] == "passed_for_local_fixture_only"
        assert item["blocks_promotion_until_later_gate"] is True


def test_write_local_data_collection_local_reviewed_fixture_persists_valid_artifact(tmp_path):
    path = write_local_data_collection_local_reviewed_fixture(artifact_dir=tmp_path)

    assert path == tmp_path / LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_FILENAME
    assert load_local_data_collection_local_reviewed_fixture(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_fixture_fails_closed_when_source_gate_promotes_readiness():
    gate = copy.deepcopy(build_local_data_collection_fixture_review_gate())
    gate["ladder_boundary"]["promotion_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source gate promoted readiness"):
        build_local_data_collection_local_reviewed_fixture(gate=gate)


def test_loader_fails_closed_on_readiness_promotion(tmp_path):
    fixture = build_local_data_collection_local_reviewed_fixture()
    fixture["readiness"]["public_service_catalog_ready"] = True
    (tmp_path / LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_local_data_collection_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    fixture = build_local_data_collection_local_reviewed_fixture()
    fixture["safe_to_claim"].append("local_data_collection_local_fixture_dataset_ready")
    (tmp_path / LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_local_data_collection_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_exact_location_payload_key(tmp_path):
    fixture = build_local_data_collection_local_reviewed_fixture()
    fixture["local_fixture"]["evidence_contract_snapshot"]["latitude"] = "redacted-but-still-keyed"
    (tmp_path / LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden payload key latitude"):
        load_local_data_collection_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_dataset_or_analytics_overclaim(tmp_path):
    fixture = build_local_data_collection_local_reviewed_fixture()
    fixture["local_fixture"]["reviewed_output"]["limitations_and_non_guarantees"].append(
        "customer dataset is ready for predictive analytics are provided"
    )
    (tmp_path / LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="overclaimed dataset or analytics"):
        load_local_data_collection_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_when_review_check_stops_blocking(tmp_path):
    fixture = build_local_data_collection_local_reviewed_fixture()
    fixture["local_review_checks"][0]["blocks_promotion_until_later_gate"] = False
    (tmp_path / LOCAL_DATA_COLLECTION_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="stopped blocking promotion"):
        load_local_data_collection_local_reviewed_fixture(artifact_dir=tmp_path)
