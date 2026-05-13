import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.document_handoff_fixture_review_gate import (
    DOCUMENT_HANDOFF_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    build_document_handoff_fixture_review_gate,
)
from mcp_server.city_ops.document_handoff_local_reviewed_fixture import (
    COVERED_LADDER_STEPS,
    DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_FILENAME,
    DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
    DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SCHEMA,
    FIXTURE_ID,
    LOCAL_FIXTURE_REVIEW_CHECKS,
    NEXT_REQUIRED_LADDER_STEPS,
    build_document_handoff_local_reviewed_fixture,
    load_document_handoff_local_reviewed_fixture,
    write_document_handoff_local_reviewed_fixture,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture() -> dict:
    with (ARTIFACT_DIR / DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_document_handoff_local_reviewed_fixture_matches_persisted_artifact():
    fixture = build_document_handoff_local_reviewed_fixture()

    assert fixture == read_fixture()
    assert load_document_handoff_local_reviewed_fixture() == fixture
    assert fixture["schema"] == DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SCHEMA
    assert fixture["fixture_id"] == FIXTURE_ID
    assert fixture["scope"] == "internal_admin_document_handoff_local_reviewed_fixture_only"
    assert fixture["offer_id"] == "document_handoff_proof_run"
    assert DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM in fixture["safe_to_claim"]
    assert DOCUMENT_HANDOFF_FIXTURE_REVIEW_GATE_SAFE_CLAIM in fixture["safe_to_claim"]
    assert AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM in fixture["safe_to_claim"]


def test_fixture_advances_exactly_one_ladder_rung_without_promotion():
    fixture = build_document_handoff_local_reviewed_fixture()

    assert fixture["ladder_boundary"]["covered_steps"] == COVERED_LADDER_STEPS
    assert fixture["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert fixture["ladder_boundary"]["promotion_allowed"] is False
    assert fixture["local_fixture"]["review_status"] == (
        "reviewed_internal_fixture_only_not_promoted"
    )


def test_fixture_populates_required_handoff_evidence_and_reviewed_output_fields():
    fixture = build_document_handoff_local_reviewed_fixture()
    local_fixture = fixture["local_fixture"]
    evidence = local_fixture["evidence_contract_snapshot"]
    reviewed_output = local_fixture["reviewed_output"]

    for field in [
        "chain_of_custody_events_inside_scoped_windows",
        "pickup_or_dropoff_timestamp",
        "recipient_or_source_type",
        "receipt_stamp_or_photo_where_available",
        "failed_handoff_reason",
        "queue_or_wait_boundary",
        "recommended_next_action",
    ]:
        assert field in evidence

    for field in local_fixture["reviewed_output_schema"]["required_fields"]:
        assert field in reviewed_output
    assert "not a legal service" in reviewed_output["plain_language_status"]
    assert "not a guarantee of acceptance" in reviewed_output["plain_language_status"]
    assert "office_counter_staff_source" in reviewed_output["recipient_or_source_type_summary"]
    assert "not acceptance" in reviewed_output["receipt_or_stamp_summary"]


def test_fixture_blocks_customer_public_dispatch_reputation_notarial_and_worker_doctrine():
    fixture = build_document_handoff_local_reviewed_fixture()
    local_fixture = fixture["local_fixture"]

    assert local_fixture["customer_copy_changed"] is False
    assert local_fixture["customer_delivery_allowed"] is False
    assert local_fixture["publication_allowed"] is False
    assert local_fixture["dispatch_allowed"] is False
    assert local_fixture["reputation_attachment_allowed"] is False
    assert local_fixture["worker_copyable_doctrine_allowed"] is False
    assert local_fixture["notarial_claim_allowed"] is False
    assert local_fixture["custody_guarantee_allowed"] is False

    for claim in [
        "customer_copy_ready",
        "public_service_catalog_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_copyable_handoff_doctrine",
        "document_handoff_local_fixture_customer_delivery_ready",
        "document_handoff_local_fixture_publication_ready",
        "document_handoff_local_fixture_notarial_ready",
        "document_handoff_local_fixture_custody_guarantee_ready",
    ]:
        assert claim in fixture["do_not_claim_yet"]
        assert claim not in fixture["safe_to_claim"]


def test_readiness_flags_remain_false():
    fixture = build_document_handoff_local_reviewed_fixture()

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
    fixture = build_document_handoff_local_reviewed_fixture()

    assert [item["check_id"] for item in fixture["local_review_checks"]] == (
        LOCAL_FIXTURE_REVIEW_CHECKS
    )
    for item in fixture["local_review_checks"]:
        assert item["status"] == "passed_for_local_fixture_only"
        assert item["blocks_promotion_until_later_gate"] is True


def test_write_document_handoff_local_reviewed_fixture_persists_valid_artifact(tmp_path):
    path = write_document_handoff_local_reviewed_fixture(artifact_dir=tmp_path)

    assert path == tmp_path / DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_FILENAME
    assert load_document_handoff_local_reviewed_fixture(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_fixture_fails_closed_when_source_gate_promotes_readiness():
    gate = build_document_handoff_fixture_review_gate()
    gate = copy.deepcopy(gate)
    gate["ladder_boundary"]["promotion_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source gate promoted readiness"):
        build_document_handoff_local_reviewed_fixture(gate=gate)


def test_loader_fails_closed_on_readiness_promotion(tmp_path):
    fixture = build_document_handoff_local_reviewed_fixture()
    fixture["readiness"]["public_service_catalog_ready"] = True
    (tmp_path / DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_document_handoff_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    fixture = build_document_handoff_local_reviewed_fixture()
    fixture["safe_to_claim"].append("document_handoff_local_fixture_publication_ready")
    (tmp_path / DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_document_handoff_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_private_identity_language(tmp_path):
    fixture = build_document_handoff_local_reviewed_fixture()
    fixture["local_fixture"]["reviewed_output"]["recipient_or_source_type_summary"] = (
        "driver license was copied for the handoff"
    )
    (tmp_path / DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="private location, identity"):
        load_document_handoff_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_custody_overclaim(tmp_path):
    fixture = build_document_handoff_local_reviewed_fixture()
    fixture["local_fixture"]["reviewed_output"]["limitations_and_non_guarantees"].append(
        "custody guaranteed until final filing success confirmed"
    )
    (tmp_path / DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="handoff overclaim"):
        load_document_handoff_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_when_review_check_stops_blocking(tmp_path):
    fixture = build_document_handoff_local_reviewed_fixture()
    fixture["local_review_checks"][0]["blocks_promotion_until_later_gate"] = False
    (tmp_path / DOCUMENT_HANDOFF_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="stopped blocking promotion"):
        load_document_handoff_local_reviewed_fixture(artifact_dir=tmp_path)
