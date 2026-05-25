import copy
import hashlib
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.local_data_collection_internal_package_record import (
    LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_FILENAME,
    LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    build_local_data_collection_internal_package_record,
)
from mcp_server.city_ops.local_data_collection_operator_read_surface import (
    COVERED_LADDER_STEPS,
    NEXT_REQUIRED_LADDER_STEPS,
    LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME,
    LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_SAFE_CLAIM,
    LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_SCHEMA,
    SURFACE_ID,
    build_local_data_collection_operator_read_surface,
    load_local_data_collection_operator_read_surface,
    write_local_data_collection_operator_read_surface,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_surface() -> dict:
    with (ARTIFACT_DIR / LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def digest_record(record: dict) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_local_data_collection_operator_read_surface_matches_persisted_artifact():
    surface = build_local_data_collection_operator_read_surface()

    assert surface == read_surface()
    assert load_local_data_collection_operator_read_surface() == surface
    assert surface["schema"] == LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_SCHEMA
    assert surface["surface_id"] == SURFACE_ID
    assert surface["scope"] == "internal_admin_local_data_collection_read_surface_only"
    assert surface["offer_id"] == "one_window_count_or_measurement_snapshot"
    assert LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_SAFE_CLAIM in surface["safe_to_claim"]
    assert LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in surface["safe_to_claim"]


def test_read_surface_advances_exactly_one_ladder_rung_without_promotion():
    surface = build_local_data_collection_operator_read_surface()

    assert surface["ladder_boundary"]["covered_steps"] == COVERED_LADDER_STEPS
    assert surface["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert surface["ladder_boundary"]["promotion_allowed"] is False
    assert surface["surface_status"] == (
        "read_only_operator_surface_landed_not_dataset_not_customer_ready"
    )


def test_read_surface_consumes_only_internal_package_record_and_preserves_digest():
    package_record = build_local_data_collection_internal_package_record()
    surface = build_local_data_collection_operator_read_surface(package_record=package_record)

    assert surface["derived_from"]["read_only"] is True
    assert surface["derived_from"]["source_artifacts"] == [
        LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_FILENAME
    ]
    assert surface["derived_from"]["consumes_only"] == [
        LOCAL_DATA_COLLECTION_INTERNAL_PACKAGE_RECORD_FILENAME
    ]
    assert surface["derived_from"]["reads_raw_review_fixtures"] is False
    assert surface["derived_from"]["reads_raw_transcripts"] is False
    assert surface["derived_from"]["reads_unreviewed_sensor_data"] is False
    assert surface["derived_from"]["semantic_reinterpretation_performed"] is False
    assert surface["source_package_digest_sha256"] == digest_record(package_record)
    assert surface["derived_from"]["source_artifact_lineage_passed_through"] == (
        package_record["internal_package_record"]["source_artifacts"]
    )


def test_safe_and_blocked_claims_are_adjacent_in_persisted_surface():
    path = ARTIFACT_DIR / LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME
    loaded_with_order = json.loads(path.read_text(encoding="utf-8"))
    keys = list(loaded_with_order.keys())

    assert keys.index("do_not_claim_yet") == keys.index("safe_to_claim") + 1
    assert loaded_with_order["operator_cards"][-2]["card"] == "safe_to_claim"
    assert loaded_with_order["operator_cards"][-1]["card"] == "do_not_claim_yet"


def test_read_surface_access_policy_is_internal_admin_only_and_route_not_registered():
    surface = build_local_data_collection_operator_read_surface()
    access = surface["access_policy"]

    assert access["audience"] == "internal_admin_only"
    assert access["requires_admin_context"] is True
    assert access["network_route_registered"] is False
    assert access["public_route_registered"] is False
    assert access["customer_visible"] is False
    assert access["catalog_visible"] is False
    assert access["dataset_visible"] is False
    assert access["analytics_visible"] is False
    assert access["pricing_enabled"] is False
    assert access["worker_visible"] is False
    assert access["dispatch_enabled"] is False
    assert access["writes_live_acontext"] is False
    assert access["emits_reputation_receipts"] is False
    assert access["exposes_gps_or_metadata"] is False
    assert access["publishes_worker_doctrine"] is False
    assert access["claims_statistical_representativeness"] is False
    assert access["claims_continuous_monitoring"] is False
    assert access["claims_official_dataset_certification"] is False
    assert access["claims_predictive_analytics"] is False
    assert access["claims_exactness_certification"] is False
    assert surface["mount_contract"]["network_route_registered"] is False


def test_read_surface_cards_are_pass_through_not_customer_copy_or_dataset():
    package_record = build_local_data_collection_internal_package_record()
    surface = build_local_data_collection_operator_read_surface(package_record=package_record)
    cards = {card["card"]: card for card in surface["operator_cards"]}

    assert cards["evidence_contract"]["values"] == package_record[
        "internal_package_record"
    ]["packaged_evidence_contract"]
    assert cards["reviewed_output"]["values"] == package_record[
        "internal_package_record"
    ]["packaged_reviewed_output"]
    assert cards["reviewed_output"]["status"] == (
        "package_payload_pass_through_not_customer_copy_or_dataset"
    )
    assert cards["source_artifact_lineage"]["values"]["source_package_digest_sha256"] == (
        digest_record(package_record)
    )
    assert cards["package_state"]["status"] == "package_state_pass_through_all_false"
    assert all(value is False for value in cards["package_state"]["values"].values())


def test_read_surface_blocks_external_product_data_and_worker_claims():
    surface = build_local_data_collection_operator_read_surface()
    blocked = set(surface["do_not_claim_yet"])

    for claim in [
        "read_surface_public_route_ready",
        "read_surface_customer_delivery_ready",
        "read_surface_catalog_ready",
        "read_surface_dataset_ready",
        "read_surface_analytics_ready",
        "read_surface_pricing_ready",
        "read_surface_dispatch_ready",
        "read_surface_reputation_ready",
        "read_surface_worker_doctrine_ready",
        "read_surface_statistical_representativeness_ready",
        "read_surface_continuous_monitoring_ready",
        "read_surface_official_dataset_certification_ready",
        "read_surface_predictive_analytics_ready",
        "read_surface_exactness_certification_ready",
        "customer_copy_ready",
        "public_service_catalog_ready",
        "public_dataset_ready",
        "analytics_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_copyable_data_collection_doctrine",
        "exact_gps_or_raw_metadata_exposure_allowed",
        "statistical_representativeness",
        "continuous_monitoring",
        "official_dataset_certification",
        "predictive_analytics",
        "exactness_beyond_observed_method",
    ]:
        assert claim in blocked
        assert claim not in surface["safe_to_claim"]
    assert all(value is False for value in surface["readiness"].values())


def test_read_surface_coverage_summary_keeps_promotion_blocked():
    surface = build_local_data_collection_operator_read_surface()
    summary = surface["coverage_summary"]

    assert summary["covered_package_records"] == 1
    assert summary["source_fixture_count"] == 1
    assert summary["review_status"] == "packaged_internal_only_not_promoted"
    assert summary["operator_cards_are_pass_through"] is True
    assert summary["package_state_passed_through_without_reinterpretation"] is True
    assert summary["customer_dataset_or_analytics_created"] is False
    assert summary["promotion_blocked_until_separate_artifacts"] is True


def test_write_local_data_collection_operator_read_surface_persists_valid_artifact(tmp_path):
    path = write_local_data_collection_operator_read_surface(artifact_dir=tmp_path)

    assert path == tmp_path / LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME
    assert load_local_data_collection_operator_read_surface(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_read_surface_fails_closed_when_source_package_promotes_readiness():
    package = copy.deepcopy(build_local_data_collection_internal_package_record())
    package["readiness"]["public_service_catalog_ready"] = True

    with pytest.raises(CityOpsContractError, match="source promoted readiness"):
        build_local_data_collection_operator_read_surface(package_record=package)


def test_read_surface_fails_closed_when_source_package_promotes_data_claim():
    package = copy.deepcopy(build_local_data_collection_internal_package_record())
    package["internal_package_record"]["analytics_publication_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source promoted"):
        build_local_data_collection_operator_read_surface(package_record=package)


def test_loader_fails_closed_on_public_access_upgrade(tmp_path):
    surface = build_local_data_collection_operator_read_surface()
    surface["access_policy"]["public_route_registered"] = True
    (tmp_path / LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="access_policy overclaims"):
        load_local_data_collection_operator_read_surface(artifact_dir=tmp_path)


def test_loader_fails_closed_on_customer_dataset_relabel(tmp_path):
    surface = build_local_data_collection_operator_read_surface()
    for card in surface["operator_cards"]:
        if card["card"] == "reviewed_output":
            card["status"] = "customer_dataset_ready"
    (tmp_path / LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted reviewed output"):
        load_local_data_collection_operator_read_surface(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    surface = build_local_data_collection_operator_read_surface()
    surface["safe_to_claim"].append("read_surface_dispatch_ready")
    (tmp_path / LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_local_data_collection_operator_read_surface(artifact_dir=tmp_path)


def test_loader_fails_closed_when_claim_lists_are_not_adjacent(tmp_path):
    surface = build_local_data_collection_operator_read_surface()
    reordered = {}
    for key, value in surface.items():
        if key == "do_not_claim_yet":
            continue
        reordered[key] = value
        if key == "ladder_boundary":
            reordered["do_not_claim_yet"] = surface["do_not_claim_yet"]
    (tmp_path / LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(reordered), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="separated claim boundaries"):
        load_local_data_collection_operator_read_surface(artifact_dir=tmp_path)


def test_loader_fails_closed_on_exact_location_language(tmp_path):
    surface = build_local_data_collection_operator_read_surface()
    surface["coverage_summary"]["bad_note"] = "latitude retained"
    (tmp_path / LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="private metadata or overclaimed"):
        load_local_data_collection_operator_read_surface(artifact_dir=tmp_path)


def test_loader_fails_closed_on_dataset_or_analytics_overclaim_language(tmp_path):
    surface = build_local_data_collection_operator_read_surface()
    surface["operator_instruction"] += " customer dataset authorized"
    (tmp_path / LOCAL_DATA_COLLECTION_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="private metadata or overclaimed"):
        load_local_data_collection_operator_read_surface(artifact_dir=tmp_path)
