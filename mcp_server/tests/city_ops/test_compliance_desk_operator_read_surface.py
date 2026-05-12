import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.compliance_desk_internal_package_record import (
    COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_FILENAME,
    COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM,
    build_compliance_desk_internal_package_record,
)
from mcp_server.city_ops.compliance_desk_operator_read_surface import (
    COMPLIANCE_DESK_OPERATOR_READ_SURFACE_FILENAME,
    COMPLIANCE_DESK_OPERATOR_READ_SURFACE_SAFE_CLAIM,
    COMPLIANCE_DESK_OPERATOR_READ_SURFACE_SCHEMA,
    COVERED_LADDER_STEPS,
    NEXT_REQUIRED_LADDER_STEPS,
    SURFACE_ID,
    build_compliance_desk_operator_read_surface,
    load_compliance_desk_operator_read_surface,
    write_compliance_desk_operator_read_surface,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_surface() -> dict:
    with (ARTIFACT_DIR / COMPLIANCE_DESK_OPERATOR_READ_SURFACE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_compliance_desk_operator_read_surface_matches_persisted_artifact():
    surface = build_compliance_desk_operator_read_surface()

    assert surface == read_surface()
    assert load_compliance_desk_operator_read_surface() == surface
    assert surface["schema"] == COMPLIANCE_DESK_OPERATOR_READ_SURFACE_SCHEMA
    assert surface["surface_id"] == SURFACE_ID
    assert surface["scope"] == "internal_admin_compliance_desk_read_surface_only"
    assert surface["offer_id"] == "visible_posting_notice_compliance_snapshot"
    assert COMPLIANCE_DESK_OPERATOR_READ_SURFACE_SAFE_CLAIM in surface["safe_to_claim"]
    assert COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_SAFE_CLAIM in surface["safe_to_claim"]


def test_read_surface_advances_exactly_one_ladder_rung_without_promotion():
    surface = build_compliance_desk_operator_read_surface()

    assert surface["ladder_boundary"]["covered_steps"] == COVERED_LADDER_STEPS
    assert surface["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert surface["ladder_boundary"]["promotion_allowed"] is False
    assert surface["surface_status"] == (
        "read_only_operator_surface_landed_not_public_not_customer_ready"
    )


def test_read_surface_consumes_only_internal_package_record():
    surface = build_compliance_desk_operator_read_surface()

    assert surface["derived_from"]["read_only"] is True
    assert surface["derived_from"]["source_artifacts"] == [
        COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_FILENAME
    ]
    assert surface["derived_from"]["consumes_only"] == [
        COMPLIANCE_DESK_INTERNAL_PACKAGE_RECORD_FILENAME
    ]
    assert surface["derived_from"]["reads_raw_transcripts"] is False
    assert surface["derived_from"]["reads_raw_review_fixtures"] is False
    assert surface["derived_from"]["semantic_reinterpretation_performed"] is False


def test_read_surface_access_policy_is_internal_admin_only_and_route_not_registered():
    surface = build_compliance_desk_operator_read_surface()
    access = surface["access_policy"]

    assert access["audience"] == "internal_admin_only"
    assert access["requires_admin_context"] is True
    assert access["network_route_registered"] is False
    assert access["public_route_registered"] is False
    assert access["customer_visible"] is False
    assert access["worker_visible"] is False
    assert access["dispatch_enabled"] is False
    assert access["writes_live_acontext"] is False
    assert access["emits_reputation_receipts"] is False
    assert access["exposes_gps_or_metadata"] is False
    assert access["publishes_worker_doctrine"] is False
    assert surface["mount_contract"]["network_route_registered"] is False


def test_read_surface_cards_are_pass_through_not_customer_copy():
    package_record = build_compliance_desk_internal_package_record()
    surface = build_compliance_desk_operator_read_surface(package_record=package_record)
    cards = {card["card"]: card for card in surface["operator_cards"]}

    assert cards["evidence_contract"]["values"] == package_record[
        "internal_package_record"
    ]["packaged_evidence_contract"]
    assert cards["reviewed_output"]["values"] == package_record[
        "internal_package_record"
    ]["packaged_reviewed_output"]
    assert cards["reviewed_output"]["status"] == (
        "package_payload_pass_through_not_customer_copy"
    )
    assert cards["reviewed_output"]["values"]["source_type_split"][
        "raw_transcript_used_as_authority"
    ] is False
    assert cards["limitations"]["status"] == "visible_without_softening"


def test_read_surface_blocks_external_product_and_worker_claims():
    surface = build_compliance_desk_operator_read_surface()
    blocked = set(surface["do_not_claim_yet"])

    for claim in [
        "read_surface_public_route_ready",
        "read_surface_customer_delivery_ready",
        "read_surface_dispatch_ready",
        "read_surface_reputation_ready",
        "read_surface_worker_doctrine_ready",
        "customer_copy_ready",
        "public_service_catalog_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_copyable_compliance_doctrine",
        "exact_gps_or_raw_metadata_exposure_allowed",
    ]:
        assert claim in blocked
        assert claim not in surface["safe_to_claim"]
    assert all(value is False for value in surface["readiness"].values())


def test_read_surface_coverage_summary_keeps_promotion_blocked():
    surface = build_compliance_desk_operator_read_surface()
    summary = surface["coverage_summary"]

    assert summary["covered_package_records"] == 1
    assert summary["source_fixture_count"] == 1
    assert summary["review_status"] == "packaged_internal_only_not_promoted"
    assert summary["partial_legibility_blocks_promotion"] is True
    assert summary["operator_cards_are_pass_through"] is True


def test_write_compliance_desk_operator_read_surface_persists_valid_artifact(tmp_path):
    path = write_compliance_desk_operator_read_surface(artifact_dir=tmp_path)

    assert path == tmp_path / COMPLIANCE_DESK_OPERATOR_READ_SURFACE_FILENAME
    assert load_compliance_desk_operator_read_surface(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_read_surface_fails_closed_when_source_package_promotes_readiness():
    package = copy.deepcopy(build_compliance_desk_internal_package_record())
    package["readiness"]["public_service_catalog_ready"] = True

    with pytest.raises(CityOpsContractError, match="source promoted readiness"):
        build_compliance_desk_operator_read_surface(package_record=package)


def test_loader_fails_closed_on_public_access_upgrade(tmp_path):
    surface = build_compliance_desk_operator_read_surface()
    surface["access_policy"]["public_route_registered"] = True
    (tmp_path / COMPLIANCE_DESK_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="access_policy overclaims"):
        load_compliance_desk_operator_read_surface(artifact_dir=tmp_path)


def test_loader_fails_closed_on_customer_copy_relabel(tmp_path):
    surface = build_compliance_desk_operator_read_surface()
    for card in surface["operator_cards"]:
        if card["card"] == "reviewed_output":
            card["status"] = "customer_copy_ready"
    (tmp_path / COMPLIANCE_DESK_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted reviewed output"):
        load_compliance_desk_operator_read_surface(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    surface = build_compliance_desk_operator_read_surface()
    surface["safe_to_claim"].append("read_surface_dispatch_ready")
    (tmp_path / COMPLIANCE_DESK_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_compliance_desk_operator_read_surface(artifact_dir=tmp_path)


def test_loader_fails_closed_on_exact_location_language(tmp_path):
    surface = build_compliance_desk_operator_read_surface()
    for card in surface["operator_cards"]:
        if card["card"] == "reviewed_output":
            card["values"]["evidence_summary"].append("latitude and longitude retained")
    (tmp_path / COMPLIANCE_DESK_OPERATOR_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="exact location"):
        load_compliance_desk_operator_read_surface(artifact_dir=tmp_path)
