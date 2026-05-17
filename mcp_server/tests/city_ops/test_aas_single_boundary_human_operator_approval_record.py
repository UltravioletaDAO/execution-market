import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_single_boundary_approval_record_schema_gate import (
    FUTURE_RECORD_MUST_KEEP_FALSE,
    REQUIRED_REDACTION_CHECKS,
)
from mcp_server.city_ops.aas_single_boundary_approval_record_validator import (
    APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
    APPROVAL_RECORD_ALLOWED_SCOPE,
    APPROVAL_RECORD_ALLOWED_STATUS,
    build_aas_single_boundary_approval_record_validator,
    validate_aas_single_boundary_human_operator_approval_record,
)
from mcp_server.city_ops.aas_single_boundary_human_operator_approval_record import (
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA,
    APPROVED_TEXT_BOUNDARY,
    APPROVED_TEXT_FIELDS,
    EXACT_APPROVED_TEXT,
    RECORD_STILL_BLOCKED_CLAIMS,
    build_aas_single_boundary_human_operator_approval_record,
    load_aas_single_boundary_human_operator_approval_record,
    write_aas_single_boundary_human_operator_approval_record,
)
from mcp_server.city_ops.aas_single_boundary_operator_review_brief import (
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME,
    build_aas_single_boundary_operator_review_brief,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_record() -> dict:
    with (ARTIFACT_DIR / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    brief = build_aas_single_boundary_operator_review_brief()
    (tmp_path / AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME).write_text(
        json.dumps(brief), encoding="utf-8"
    )
    validator = build_aas_single_boundary_approval_record_validator(source_brief=brief)
    (tmp_path / "aas_single_boundary_approval_record_validator.json").write_text(
        json.dumps(validator), encoding="utf-8"
    )


def test_record_matches_persisted_artifact_and_loader():
    record = build_aas_single_boundary_human_operator_approval_record()

    assert record == read_record()
    assert load_aas_single_boundary_human_operator_approval_record() == record
    assert record["schema"] == AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SCHEMA
    assert record["record_status"] == APPROVAL_RECORD_ALLOWED_STATUS
    assert AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM in record[
        "safe_to_claim"
    ]


def test_record_approves_only_exact_internal_package_label_boundary():
    record = build_aas_single_boundary_human_operator_approval_record()

    assert record["selected_boundary_key"] == "compliance_desk"
    assert record["offer_id"] == "visible_posting_notice_compliance_snapshot"
    assert record["approved_text_boundary"] == APPROVED_TEXT_BOUNDARY
    assert record["exact_approved_text"] == EXACT_APPROVED_TEXT
    assert record["approved_text_fields"] == APPROVED_TEXT_FIELDS
    assert record["approved_text_sections"] == [
        {
            "section": APPROVED_TEXT_BOUNDARY,
            "approved_text": EXACT_APPROVED_TEXT,
            "approved_fields": APPROVED_TEXT_FIELDS,
        }
    ]
    assert record["human_operator_approval_recorded"] is True
    assert record["selected_boundary_approved"] is True


def test_record_passes_validator_but_authorizes_no_delivery_publication_or_dispatch():
    record = build_aas_single_boundary_human_operator_approval_record()

    result = validate_aas_single_boundary_human_operator_approval_record(record)

    assert result == {
        "record_valid": True,
        "validated_scope": APPROVAL_RECORD_ALLOWED_SCOPE,
        "selected_boundary_key": "compliance_desk",
        "exact_text_approved": EXACT_APPROVED_TEXT,
        "customer_delivery_authorized": False,
        "publication_authorized": False,
        "dispatch_authorized": False,
        "reputation_authorized": False,
        "runtime_or_acontext_authorized": False,
    }
    assert record["authorized_delivery_path"] == APPROVAL_RECORD_ALLOWED_DELIVERY_PATH
    for field in [
        "customer_delivery_allowed",
        "public_route_allowed",
        "catalog_route_allowed",
        "dispatch_allowed",
        "reputation_attachment_allowed",
        "exact_gps_or_raw_metadata_allowed",
    ]:
        assert record["authorized_delivery_path_detail"][field] is False


def test_redactions_are_passed_with_non_secret_evidence_references():
    record = build_aas_single_boundary_human_operator_approval_record()

    assert [item["check"] for item in record["redaction_checks_passed"]] == (
        REQUIRED_REDACTION_CHECKS
    )
    for item in record["redaction_checks_passed"]:
        assert item["passed"] is True
        assert item["evidence_reference"].startswith("operator_redaction_review:")
        assert "gps" not in item["evidence_reference"].lower() or item["check"] == "exact_gps_removed"


def test_sticky_claim_lists_preserve_safe_and_blocked_boundaries():
    record = build_aas_single_boundary_human_operator_approval_record()

    for claim in RECORD_STILL_BLOCKED_CLAIMS:
        assert claim in record["do_not_claim_yet"]
        assert claim not in record["safe_to_claim"]
    assert record["still_blocked_claims"] == record["do_not_claim_yet"]
    assert "customer_delivery_approved" in record["do_not_claim_yet"]
    assert "publication_approved" in record["do_not_claim_yet"]
    assert "dispatch_enabled" in record["do_not_claim_yet"]
    assert "erc8004_reputation_ready" in record["do_not_claim_yet"]
    assert "exact_gps_or_raw_metadata_exposure_allowed" in record["do_not_claim_yet"]


def test_false_flags_remain_false():
    record = build_aas_single_boundary_human_operator_approval_record()

    assert record["approvals_not_granted"] == list(FUTURE_RECORD_MUST_KEEP_FALSE)
    for flag in FUTURE_RECORD_MUST_KEEP_FALSE:
        assert record["future_record_must_keep_false"][flag] is False
    for flag in [
        "customer_delivery_authorized",
        "operator_publish_approval",
        "publication_approved",
        "public_route_ready",
        "catalog_route_ready",
        "controlled_pilot_ready",
        "front_door_sku_ready",
        "public_price_approved",
        "customer_quote_ready",
        "operator_queue_launch_ready",
        "dispatch_enabled",
        "autonomous_dispatch_ready",
        "reputation_ready",
        "erc8004_reputation_ready",
        "live_acontext_ready",
        "runtime_parity_proven",
        "exact_gps_or_raw_metadata_exposure_allowed",
        "domain_authority_claims_allowed",
        "worker_skill_dna_ready",
        "worker_copyable_doctrine_ready",
    ]:
        assert record[flag] is False


def test_write_record_persists_valid_artifact(tmp_path):
    seed_sources(tmp_path)

    path = write_aas_single_boundary_human_operator_approval_record(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME
    assert load_aas_single_boundary_human_operator_approval_record(
        artifact_dir=tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_source_brief_text_drift_fails_closed():
    brief = build_aas_single_boundary_operator_review_brief()
    validator = build_aas_single_boundary_approval_record_validator(source_brief=brief)
    brief = copy.deepcopy(brief)
    brief["selected_boundary"]["exact_text_under_review"] = "Different label"

    with pytest.raises(CityOpsContractError, match="source brief digest drift"):
        build_aas_single_boundary_human_operator_approval_record(
            source_brief=brief,
            source_validator=validator,
        )


def test_source_validator_forbidden_safe_claim_fails_closed():
    brief = build_aas_single_boundary_operator_review_brief()
    validator = build_aas_single_boundary_approval_record_validator(source_brief=brief)
    validator = copy.deepcopy(validator)
    validator["safe_to_claim"].append("customer_delivery_ready")

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        build_aas_single_boundary_human_operator_approval_record(
            source_brief=brief,
            source_validator=validator,
        )


def test_loader_rejects_delivery_promotion(tmp_path):
    seed_sources(tmp_path)
    record = build_aas_single_boundary_human_operator_approval_record(artifact_dir=tmp_path)
    record["customer_delivery_approved"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden promotion customer_delivery_approved"):
        load_aas_single_boundary_human_operator_approval_record(artifact_dir=tmp_path)


def test_loader_rejects_missing_redaction_evidence(tmp_path):
    seed_sources(tmp_path)
    record = build_aas_single_boundary_human_operator_approval_record(artifact_dir=tmp_path)
    record["redaction_checks_passed"][0]["evidence_reference"] = ""
    (tmp_path / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="redaction evidence reference"):
        load_aas_single_boundary_human_operator_approval_record(artifact_dir=tmp_path)


def test_loader_rejects_missing_blocked_claim(tmp_path):
    seed_sources(tmp_path)
    record = build_aas_single_boundary_human_operator_approval_record(artifact_dir=tmp_path)
    record["do_not_claim_yet"].remove("approval_record_authorizes_dispatch")
    record["still_blocked_claims"] = record["do_not_claim_yet"]
    (tmp_path / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="missing blocked claims"):
        load_aas_single_boundary_human_operator_approval_record(artifact_dir=tmp_path)
