import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
)
from mcp_server.city_ops.compliance_desk_fixture_review_gate import (
    COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    build_compliance_desk_fixture_review_gate,
)
from mcp_server.city_ops.compliance_desk_local_reviewed_fixture import (
    COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME,
    COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM,
    COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SCHEMA,
    COVERED_LADDER_STEPS,
    FIXTURE_ID,
    LOCAL_FIXTURE_REVIEW_CHECKS,
    NEXT_REQUIRED_LADDER_STEPS,
    build_compliance_desk_local_reviewed_fixture,
    load_compliance_desk_local_reviewed_fixture,
    write_compliance_desk_local_reviewed_fixture,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture() -> dict:
    with (ARTIFACT_DIR / COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_compliance_desk_local_reviewed_fixture_matches_persisted_artifact():
    fixture = build_compliance_desk_local_reviewed_fixture()

    assert fixture == read_fixture()
    assert load_compliance_desk_local_reviewed_fixture() == fixture
    assert fixture["schema"] == COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SCHEMA
    assert fixture["fixture_id"] == FIXTURE_ID
    assert fixture["scope"] == "internal_admin_compliance_desk_local_reviewed_fixture_only"
    assert fixture["offer_id"] == "visible_posting_notice_compliance_snapshot"
    assert COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_SAFE_CLAIM in fixture["safe_to_claim"]
    assert COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM in fixture["safe_to_claim"]
    assert AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM in fixture["safe_to_claim"]


def test_fixture_advances_exactly_one_ladder_rung_without_promotion():
    fixture = build_compliance_desk_local_reviewed_fixture()

    assert fixture["ladder_boundary"]["covered_steps"] == COVERED_LADDER_STEPS
    assert fixture["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert fixture["ladder_boundary"]["promotion_allowed"] is False
    assert fixture["local_fixture"]["review_status"] == (
        "reviewed_internal_fixture_only_not_promoted"
    )


def test_fixture_populates_required_evidence_and_reviewed_output_fields():
    fixture = build_compliance_desk_local_reviewed_fixture()
    local_fixture = fixture["local_fixture"]
    evidence = local_fixture["evidence_contract_snapshot"]
    reviewed_output = local_fixture["reviewed_output"]

    for field in [
        "wide_context_photo_or_permitted_visual_snapshot",
        "close_notice_or_required_element_photo_where_allowed",
        "timestamp_window",
        "visible_element_checklist",
        "source_type_observed_documented_or_heard",
        "obstruction_or_legibility_notes",
        "reviewed_limitations",
    ]:
        assert field in evidence

    for field in local_fixture["reviewed_output_schema"]["required_fields"]:
        assert field in reviewed_output
    assert reviewed_output["source_type_split"]["raw_transcript_used_as_authority"] is False
    assert "not a legal compliance finding" in reviewed_output["plain_language_status"]
    assert "no_exact_address_or_gps_in_output" in reviewed_output["visible_elements_reviewed"]


def test_fixture_blocks_customer_public_dispatch_reputation_and_worker_doctrine():
    fixture = build_compliance_desk_local_reviewed_fixture()
    local_fixture = fixture["local_fixture"]

    assert local_fixture["customer_copy_changed"] is False
    assert local_fixture["customer_delivery_allowed"] is False
    assert local_fixture["publication_allowed"] is False
    assert local_fixture["dispatch_allowed"] is False
    assert local_fixture["reputation_attachment_allowed"] is False
    assert local_fixture["worker_copyable_doctrine_allowed"] is False

    for claim in [
        "customer_copy_ready",
        "public_service_catalog_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_copyable_compliance_doctrine",
        "local_fixture_customer_delivery_ready",
        "local_fixture_publication_ready",
    ]:
        assert claim in fixture["do_not_claim_yet"]
        assert claim not in fixture["safe_to_claim"]


def test_readiness_flags_remain_false():
    fixture = build_compliance_desk_local_reviewed_fixture()

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
    fixture = build_compliance_desk_local_reviewed_fixture()

    assert [item["check_id"] for item in fixture["local_review_checks"]] == (
        LOCAL_FIXTURE_REVIEW_CHECKS
    )
    for item in fixture["local_review_checks"]:
        assert item["status"] == "passed_for_local_fixture_only"
        assert item["blocks_promotion_until_later_gate"] is True


def test_write_compliance_desk_local_reviewed_fixture_persists_valid_artifact(tmp_path):
    path = write_compliance_desk_local_reviewed_fixture(artifact_dir=tmp_path)

    assert path == tmp_path / COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME
    assert load_compliance_desk_local_reviewed_fixture(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_fixture_fails_closed_when_source_gate_promotes_readiness():
    gate = build_compliance_desk_fixture_review_gate()
    gate = copy.deepcopy(gate)
    gate["ladder_boundary"]["promotion_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source gate promoted readiness"):
        build_compliance_desk_local_reviewed_fixture(gate=gate)


def test_loader_fails_closed_on_readiness_promotion(tmp_path):
    fixture = build_compliance_desk_local_reviewed_fixture()
    fixture["readiness"]["public_service_catalog_ready"] = True
    (tmp_path / COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_compliance_desk_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    fixture = build_compliance_desk_local_reviewed_fixture()
    fixture["safe_to_claim"].append("local_fixture_publication_ready")
    (tmp_path / COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_compliance_desk_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_on_exact_location_language(tmp_path):
    fixture = build_compliance_desk_local_reviewed_fixture()
    fixture["local_fixture"]["reviewed_output"]["evidence_summary"].append(
        "latitude and longitude were available"
    )
    (tmp_path / COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="exact location"):
        load_compliance_desk_local_reviewed_fixture(artifact_dir=tmp_path)


def test_loader_fails_closed_when_review_check_stops_blocking(tmp_path):
    fixture = build_compliance_desk_local_reviewed_fixture()
    fixture["local_review_checks"][0]["blocks_promotion_until_later_gate"] = False
    (tmp_path / COMPLIANCE_DESK_LOCAL_REVIEWED_FIXTURE_FILENAME).write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="stopped blocking promotion"):
        load_compliance_desk_local_reviewed_fixture(artifact_dir=tmp_path)
