import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_packet_submission_internal_package_record import (
    PACKAGE_ID,
    PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME,
    PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SCHEMA,
    build_phase1_packet_submission_internal_package_record,
    load_phase1_packet_submission_internal_package_record,
    write_phase1_packet_submission_internal_package_record,
)
from mcp_server.city_ops.phase1_reviewed_fixtures import (
    PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME,
    PACKET_SUBMISSION_ATTEMPT_FIXTURE_ID,
    PACKET_SUBMISSION_ATTEMPT_REVIEWED_FIXTURE_SAFE_CLAIM,
    build_packet_submission_attempt_reviewed_fixture,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_package_record() -> dict:
    with (
        REVIEWED_FIXTURE_DIR / PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_packet_submission_internal_package_record_matches_persisted_artifact():
    record = build_phase1_packet_submission_internal_package_record()

    assert record == read_package_record()
    assert load_phase1_packet_submission_internal_package_record() == record
    assert record["schema"] == PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SCHEMA
    assert record["package_id"] == PACKAGE_ID
    assert record["offer"] == "packet_submission_attempt"
    assert record["promotion_level"] == "controlled_concierge_pilot_candidate"
    assert record["proof_status_label"] == "local_anchor_supported_redirect_outdated_packet_only"
    assert record["reviewed_fixture_ids"] == [PACKET_SUBMISSION_ATTEMPT_FIXTURE_ID]
    assert PACKET_SUBMISSION_ATTEMPT_REVIEWED_FIXTURE_SAFE_CLAIM in record["safe_to_claim"]
    assert PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in record[
        "safe_to_claim"
    ]


def test_packet_submission_package_record_keeps_safe_and_blocked_claims_adjacent():
    record = build_phase1_packet_submission_internal_package_record()
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


def test_packet_submission_package_record_preserves_all_readiness_flags_false():
    record = build_phase1_packet_submission_internal_package_record()

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


def test_packet_submission_package_record_sources_only_reviewed_fixture_artifact():
    record = build_phase1_packet_submission_internal_package_record()

    assert record["source_reviewed_artifacts"] == [
        {
            "fixture_id": PACKET_SUBMISSION_ATTEMPT_FIXTURE_ID,
            "source_file": PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME,
            "source_schema": "city_ops.phase1_reviewed_fixture.v1",
            "outcome_status": "rejected",
            "source_type": "mixed",
            "follow_on_task_trigger": "rejection_diagnosis_resubmission_prep",
        }
    ]


def test_write_packet_submission_package_record_persists_valid_artifact(tmp_path):
    (tmp_path / PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME).write_text(
        json.dumps(build_packet_submission_attempt_reviewed_fixture()), encoding="utf-8"
    )

    path = write_phase1_packet_submission_internal_package_record(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME
    assert load_phase1_packet_submission_internal_package_record(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_packet_submission_package_record_fails_closed_on_forbidden_claim_promotion(tmp_path):
    record = build_phase1_packet_submission_internal_package_record()
    record["safe_to_claim"].append("live_acontext_ready")
    (tmp_path / PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_phase1_packet_submission_internal_package_record(fixture_dir=tmp_path)


def test_packet_submission_package_record_fails_closed_on_dropped_blocked_claim(tmp_path):
    record = build_phase1_packet_submission_internal_package_record()
    record["do_not_claim_yet"] = [
        claim for claim in record["do_not_claim_yet"] if claim != "autonomous_dispatch_ready"
    ]
    (tmp_path / PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="missing blocked claims"):
        load_phase1_packet_submission_internal_package_record(fixture_dir=tmp_path)


def test_packet_submission_package_record_fails_closed_on_missing_reviewed_fixture(tmp_path):
    with pytest.raises(CityOpsContractError, match="requires the reviewed Packet Submission Attempt fixture"):
        build_phase1_packet_submission_internal_package_record(fixture_dir=tmp_path)


def test_packet_submission_package_record_fails_closed_on_readiness_flip(tmp_path):
    record = build_phase1_packet_submission_internal_package_record()
    record["reputation_ready"] = True
    (tmp_path / PHASE1_PACKET_SUBMISSION_INTERNAL_PACKAGE_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_phase1_packet_submission_internal_package_record(fixture_dir=tmp_path)


def test_packet_submission_package_record_fails_closed_on_unreviewed_fixture_source():
    fixture = copy.deepcopy(build_packet_submission_attempt_reviewed_fixture())
    fixture["reviewed_output"]["operator_review_status"] = "draft"

    with pytest.raises(CityOpsContractError, match="requires reviewed fixture output"):
        build_phase1_packet_submission_internal_package_record(reviewed_fixture=fixture)
