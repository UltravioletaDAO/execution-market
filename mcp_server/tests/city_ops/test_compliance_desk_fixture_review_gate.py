import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_minimum_ladder_template import (
    AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM,
    build_aas_minimum_ladder_template,
)
from mcp_server.city_ops.compliance_desk_fixture_review_gate import (
    COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_FILENAME,
    COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM,
    COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SCHEMA,
    COVERED_LADDER_STEPS,
    NEXT_REQUIRED_LADDER_STEPS,
    OFFER_ID,
    PACKAGE_FAMILY_ID,
    REQUIRED_EVIDENCE_FIELDS,
    REQUIRED_OUTPUT_FIELDS,
    REVIEW_GATE_CHECKS,
    build_compliance_desk_fixture_review_gate,
    load_compliance_desk_fixture_review_gate,
    write_compliance_desk_fixture_review_gate,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_gate() -> dict:
    with (ARTIFACT_DIR / COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_compliance_desk_fixture_review_gate_matches_persisted_artifact():
    gate = build_compliance_desk_fixture_review_gate()

    assert gate == read_gate()
    assert load_compliance_desk_fixture_review_gate() == gate
    assert gate["schema"] == COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SCHEMA
    assert gate["scope"] == (
        "internal_admin_compliance_desk_fixture_spec_and_review_gate_only"
    )
    assert gate["package_family_id"] == PACKAGE_FAMILY_ID
    assert gate["fixture_spec"]["offer_id"] == OFFER_ID
    assert COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_SAFE_CLAIM in gate["safe_to_claim"]
    assert AAS_MINIMUM_LADDER_TEMPLATE_SAFE_CLAIM in gate["safe_to_claim"]


def test_gate_consumes_compliance_family_row_from_minimum_ladder():
    gate = build_compliance_desk_fixture_review_gate()

    assert gate["fixture_spec"]["family_label"] == "Compliance Desk as a Service"
    assert gate["fixture_spec"]["caas_source_pattern"] == "posting_compliance_check"
    assert gate["ladder_boundary"]["covered_steps"] == COVERED_LADDER_STEPS
    assert gate["ladder_boundary"]["next_required_steps_before_promotion"] == (
        NEXT_REQUIRED_LADDER_STEPS
    )
    assert gate["ladder_boundary"]["promotion_allowed"] is False


def test_fixture_spec_names_evidence_output_fields_and_acceptance_gate():
    gate = build_compliance_desk_fixture_review_gate()
    spec = gate["fixture_spec"]

    for field in REQUIRED_EVIDENCE_FIELDS:
        assert field in spec["required_evidence_fields"]
    for field in REQUIRED_OUTPUT_FIELDS:
        assert field in spec["reviewed_output_schema_draft"]["required_fields"]
    for forbidden_field in [
        "exact_gps_coordinates",
        "raw_metadata_blob",
        "legal_advice_or_legal_sufficiency",
        "regulator_acceptance_claim",
        "worker_copyable_compliance_doctrine",
    ]:
        assert forbidden_field in spec["reviewed_output_schema_draft"]["forbidden_fields"]
    assert spec["fixture_acceptance_gate"]["requires_local_reviewed_fixture"] is True
    assert spec["fixture_acceptance_gate"]["allows_customer_delivery"] is False
    assert spec["fixture_acceptance_gate"]["allows_publication"] is False


def test_review_checklist_blocks_promotion_and_customer_surfaces():
    gate = build_compliance_desk_fixture_review_gate()

    assert [item["check_id"] for item in gate["review_gate_checklist"]] == (
        REVIEW_GATE_CHECKS
    )
    for item in gate["review_gate_checklist"]:
        assert item["required"] is True
        assert item["status"] == "pending_future_review"
        assert item["blocks_promotion_until_passed"] is True

    for claim in [
        "customer_copy_ready",
        "public_service_catalog_ready",
        "autonomous_dispatch_ready",
        "erc8004_reputation_ready",
        "worker_copyable_compliance_doctrine",
        "exact_gps_or_raw_metadata_exposure_allowed",
    ]:
        assert claim in gate["do_not_claim_yet"]
        assert claim not in gate["safe_to_claim"]


def test_readiness_flags_remain_false():
    gate = build_compliance_desk_fixture_review_gate()

    assert gate["readiness"]["customer_copy_ready"] is False
    assert gate["readiness"]["public_service_catalog_ready"] is False
    assert gate["readiness"]["live_acontext_ready"] is False
    assert gate["readiness"]["runtime_parity_proven"] is False
    assert gate["readiness"]["autonomous_dispatch_ready"] is False
    assert gate["readiness"]["reputation_ready"] is False
    assert gate["readiness"]["worker_skill_dna_ready"] is False
    assert gate["readiness"]["worker_copyable_doctrine_ready"] is False
    assert gate["readiness"]["exact_gps_or_raw_metadata_exposure_allowed"] is False


def test_write_compliance_desk_fixture_review_gate_persists_valid_artifact(tmp_path):
    path = write_compliance_desk_fixture_review_gate(artifact_dir=tmp_path)

    assert path == tmp_path / COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_FILENAME
    assert load_compliance_desk_fixture_review_gate(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_gate_fails_closed_when_source_template_loses_compliance_family():
    template = build_aas_minimum_ladder_template()
    template["families"] = [
        row for row in template["families"] if row["family_id"] != PACKAGE_FAMILY_ID
    ]

    with pytest.raises(CityOpsContractError, match="family row missing"):
        build_compliance_desk_fixture_review_gate(template=template)


def test_gate_fails_closed_when_source_family_loses_required_evidence():
    template = build_aas_minimum_ladder_template()
    template = copy.deepcopy(template)
    row = next(row for row in template["families"] if row["family_id"] == PACKAGE_FAMILY_ID)
    row["required_evidence"].remove("visible_element_checklist")

    with pytest.raises(CityOpsContractError, match="lost required evidence"):
        build_compliance_desk_fixture_review_gate(template=template)


def test_loader_fails_closed_on_readiness_promotion(tmp_path):
    gate = build_compliance_desk_fixture_review_gate()
    gate["readiness"]["public_service_catalog_ready"] = True
    (tmp_path / COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_compliance_desk_fixture_review_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    gate = build_compliance_desk_fixture_review_gate()
    gate["safe_to_claim"].append("compliance_desk_catalog_ready")
    (tmp_path / COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_compliance_desk_fixture_review_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_dropped_blocked_claim(tmp_path):
    gate = build_compliance_desk_fixture_review_gate()
    gate["do_not_claim_yet"] = [
        claim
        for claim in gate["do_not_claim_yet"]
        if claim != "worker_copyable_compliance_doctrine"
    ]
    (tmp_path / COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="missing blocked claims"):
        load_compliance_desk_fixture_review_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_review_checklist_promotion(tmp_path):
    gate = build_compliance_desk_fixture_review_gate()
    gate["review_gate_checklist"][0]["status"] = "passed"
    (tmp_path / COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="checklist status drift"):
        load_compliance_desk_fixture_review_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_fixture_acceptance_customer_delivery(tmp_path):
    gate = build_compliance_desk_fixture_review_gate()
    gate["fixture_spec"]["fixture_acceptance_gate"]["allows_customer_delivery"] = True
    (tmp_path / COMPLIANCE_DESK_FIXTURE_REVIEW_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_compliance_desk_fixture_review_gate(artifact_dir=tmp_path)
