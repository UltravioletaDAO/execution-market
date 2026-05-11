import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_remaining_offer_internal_package_records import (
    PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_FILENAME,
    PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SCHEMA,
    PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_FILENAME,
    PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SCHEMA,
    build_phase1_counter_reality_check_internal_package_record,
    build_phase1_posting_compliance_internal_package_record,
    load_phase1_counter_reality_check_internal_package_record,
    load_phase1_posting_compliance_internal_package_record,
    write_phase1_counter_reality_check_internal_package_record,
    write_phase1_posting_compliance_internal_package_record,
)
from mcp_server.city_ops.phase1_reviewed_fixtures import (
    COUNTER_REALITY_CHECK_FIXTURE_FILENAME,
    COUNTER_REALITY_CHECK_FIXTURE_ID,
    COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
    POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME,
    POSTING_COMPLIANCE_CHECK_FIXTURE_ID,
    POSTING_COMPLIANCE_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
    build_counter_reality_check_reviewed_fixture,
    build_posting_compliance_check_reviewed_fixture,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_counter_record() -> dict:
    with (
        REVIEWED_FIXTURE_DIR / PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_posting_record() -> dict:
    with (
        REVIEWED_FIXTURE_DIR / PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_counter_reality_package_record_matches_persisted_artifact():
    record = build_phase1_counter_reality_check_internal_package_record()

    assert record == read_counter_record()
    assert load_phase1_counter_reality_check_internal_package_record() == record
    assert record["schema"] == PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SCHEMA
    assert record["offer"] == "counter_reality_check"
    assert record["proof_status_label"] == "planning_supported_needs_first_fixture"
    assert record["reviewed_fixture_ids"] == [COUNTER_REALITY_CHECK_FIXTURE_ID]
    assert COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM in record["safe_to_claim"]
    assert PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in record[
        "safe_to_claim"
    ]


def test_posting_compliance_package_record_matches_persisted_artifact():
    record = build_phase1_posting_compliance_internal_package_record()

    assert record == read_posting_record()
    assert load_phase1_posting_compliance_internal_package_record() == record
    assert record["schema"] == PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SCHEMA
    assert record["offer"] == "posting_compliance_check"
    assert record["proof_status_label"] == "planning_supported_needs_first_fixture"
    assert record["reviewed_fixture_ids"] == [POSTING_COMPLIANCE_CHECK_FIXTURE_ID]
    assert POSTING_COMPLIANCE_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM in record["safe_to_claim"]
    assert PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in record[
        "safe_to_claim"
    ]


@pytest.mark.parametrize(
    "builder",
    [
        build_phase1_counter_reality_check_internal_package_record,
        build_phase1_posting_compliance_internal_package_record,
    ],
)
def test_remaining_package_records_keep_safe_and_blocked_claims_adjacent(builder):
    record = builder()
    key_order = list(record.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert not set(record["safe_to_claim"]) & set(record["do_not_claim_yet"])
    assert "customer_copy_ready" in record["do_not_claim_yet"]
    assert "controlled_concierge_pilot_ready" in record["do_not_claim_yet"]
    assert "live_acontext_ready" in record["do_not_claim_yet"]
    assert "runtime_parity_proven" in record["do_not_claim_yet"]
    assert "autonomous_dispatch_ready" in record["do_not_claim_yet"]
    assert "reputation_ready" in record["do_not_claim_yet"]
    assert "worker_copyable_doctrine_ready" in record["do_not_claim_yet"]
    assert "exact_gps_or_raw_metadata_exposure_allowed" in record["do_not_claim_yet"]


@pytest.mark.parametrize(
    "builder",
    [
        build_phase1_counter_reality_check_internal_package_record,
        build_phase1_posting_compliance_internal_package_record,
    ],
)
def test_remaining_package_records_preserve_false_readiness_flags(builder):
    record = builder()

    assert record["customer_output_schema_reviewed"] is False
    assert record["operator_review_required_before_closure"] is True
    assert record["forbidden_claims_preserved"] is True
    assert record["live_acontext_ready"] is False
    assert record["runtime_parity_proven"] is False
    assert record["autonomous_dispatch_ready"] is False
    assert record["reputation_ready"] is False
    assert record["worker_copyable_doctrine_ready"] is False
    assert record["exact_gps_or_raw_metadata_exposure_allowed"] is False
    assert record["internal_only"] == {
        "customer_copy_changed": False,
        "public_catalog_changed": False,
        "route_wrapper_added": False,
        "uses_only_reviewed_fixture_artifacts": True,
        "raw_transcript_used": False,
        "unreviewed_memory_used": False,
        "private_operator_context_used": False,
    }


def test_counter_record_sources_only_reviewed_fixture_artifact():
    record = build_phase1_counter_reality_check_internal_package_record()

    assert record["source_reviewed_artifacts"] == [
        {
            "fixture_id": COUNTER_REALITY_CHECK_FIXTURE_ID,
            "source_file": COUNTER_REALITY_CHECK_FIXTURE_FILENAME,
            "source_schema": "city_ops.phase1_reviewed_fixture.v1",
            "outcome_status": "redirected",
            "source_type": "mixed",
            "follow_on_task_trigger": "office_redirect_follow_through",
        }
    ]


def test_posting_record_sources_only_reviewed_fixture_artifact():
    record = build_phase1_posting_compliance_internal_package_record()

    assert record["source_reviewed_artifacts"] == [
        {
            "fixture_id": POSTING_COMPLIANCE_CHECK_FIXTURE_ID,
            "source_file": POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME,
            "source_schema": "city_ops.phase1_reviewed_fixture.v1",
            "outcome_status": "verified_partial",
            "source_type": "observed",
            "follow_on_task_trigger": "posting_recheck",
        }
    ]


def test_write_remaining_package_records_persist_valid_artifacts(tmp_path):
    (tmp_path / COUNTER_REALITY_CHECK_FIXTURE_FILENAME).write_text(
        json.dumps(build_counter_reality_check_reviewed_fixture()), encoding="utf-8"
    )
    (tmp_path / POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME).write_text(
        json.dumps(build_posting_compliance_check_reviewed_fixture()), encoding="utf-8"
    )

    counter_path = write_phase1_counter_reality_check_internal_package_record(
        fixture_dir=tmp_path
    )
    posting_path = write_phase1_posting_compliance_internal_package_record(
        fixture_dir=tmp_path
    )

    assert counter_path == tmp_path / PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_FILENAME
    assert posting_path == tmp_path / PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_FILENAME
    assert load_phase1_counter_reality_check_internal_package_record(fixture_dir=tmp_path) == json.loads(
        counter_path.read_text(encoding="utf-8")
    )
    assert load_phase1_posting_compliance_internal_package_record(fixture_dir=tmp_path) == json.loads(
        posting_path.read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "builder,filename,loader",
    [
        (
            build_phase1_counter_reality_check_internal_package_record,
            PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_FILENAME,
            load_phase1_counter_reality_check_internal_package_record,
        ),
        (
            build_phase1_posting_compliance_internal_package_record,
            PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_FILENAME,
            load_phase1_posting_compliance_internal_package_record,
        ),
    ],
)
def test_remaining_package_records_fail_closed_on_forbidden_claim_promotion(
    tmp_path, builder, filename, loader
):
    record = builder()
    record["safe_to_claim"].append("customer_copy_ready")
    (tmp_path / filename).write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        loader(fixture_dir=tmp_path)


@pytest.mark.parametrize(
    "builder,filename,loader",
    [
        (
            build_phase1_counter_reality_check_internal_package_record,
            PHASE1_COUNTER_REALITY_CHECK_INTERNAL_PACKAGE_RECORD_FILENAME,
            load_phase1_counter_reality_check_internal_package_record,
        ),
        (
            build_phase1_posting_compliance_internal_package_record,
            PHASE1_POSTING_COMPLIANCE_INTERNAL_PACKAGE_RECORD_FILENAME,
            load_phase1_posting_compliance_internal_package_record,
        ),
    ],
)
def test_remaining_package_records_fail_closed_on_readiness_flip(
    tmp_path, builder, filename, loader
):
    record = builder()
    record["runtime_parity_proven"] = True
    (tmp_path / filename).write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        loader(fixture_dir=tmp_path)


def test_counter_record_fails_closed_on_unreviewed_fixture_source():
    fixture = copy.deepcopy(build_counter_reality_check_reviewed_fixture())
    fixture["reviewed_output"]["operator_review_status"] = "draft"

    with pytest.raises(CityOpsContractError, match="requires reviewed fixture output"):
        build_phase1_counter_reality_check_internal_package_record(reviewed_fixture=fixture)


def test_posting_record_fails_closed_on_gps_metadata_source_drift():
    fixture = copy.deepcopy(build_posting_compliance_check_reviewed_fixture())
    fixture["scenario"]["exact_gps_or_metadata_exposed"] = True

    with pytest.raises(CityOpsContractError, match="exact GPS"):
        build_phase1_posting_compliance_internal_package_record(reviewed_fixture=fixture)
