import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_single_boundary_approval_record_validator import (
    APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
)
from mcp_server.city_ops.aas_single_boundary_delivery_publication_gate import (
    AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_FILENAME,
    AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SAFE_CLAIM,
    AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SCHEMA,
    DELIVERY_PUBLICATION_BLOCKED_CLAIMS,
    DELIVERY_PUBLICATION_FALSE_FLAGS,
    DELIVERY_PUBLICATION_VERDICT,
    REQUIRED_DELIVERY_PUBLICATION_CHECKS,
    build_aas_single_boundary_delivery_publication_gate,
    load_aas_single_boundary_delivery_publication_gate,
    write_aas_single_boundary_delivery_publication_gate,
)
from mcp_server.city_ops.aas_single_boundary_human_operator_approval_record import (
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME,
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
    APPROVED_TEXT_BOUNDARY,
    APPROVED_TEXT_FIELDS,
    EXACT_APPROVED_TEXT,
    build_aas_single_boundary_human_operator_approval_record,
)
from mcp_server.city_ops.aas_single_boundary_operator_review_brief import (
    AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME,
    build_aas_single_boundary_operator_review_brief,
)
from mcp_server.city_ops.aas_single_boundary_approval_record_validator import (
    AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_FILENAME,
    build_aas_single_boundary_approval_record_validator,
)
from mcp_server.city_ops.aas_single_boundary_approval_record_schema_gate import (
    REQUIRED_REDACTION_CHECKS,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_gate() -> dict:
    with (ARTIFACT_DIR / AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_source_record(tmp_path: Path) -> None:
    brief = build_aas_single_boundary_operator_review_brief()
    validator = build_aas_single_boundary_approval_record_validator(source_brief=brief)
    record = build_aas_single_boundary_human_operator_approval_record(
        source_brief=brief, source_validator=validator
    )
    (tmp_path / AAS_SINGLE_BOUNDARY_OPERATOR_REVIEW_BRIEF_FILENAME).write_text(
        json.dumps(brief), encoding="utf-8"
    )
    (tmp_path / AAS_SINGLE_BOUNDARY_APPROVAL_RECORD_VALIDATOR_FILENAME).write_text(
        json.dumps(validator), encoding="utf-8"
    )
    (tmp_path / AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME).write_text(
        json.dumps(record), encoding="utf-8"
    )


def test_gate_matches_persisted_artifact_and_loader():
    gate = build_aas_single_boundary_delivery_publication_gate()

    assert gate == read_gate()
    assert load_aas_single_boundary_delivery_publication_gate() == gate
    assert gate["schema"] == AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SCHEMA
    assert gate["scope"] == "internal_admin_delivery_publication_gate_only_no_customer_exposure"
    assert gate["gate_status"] == "blocked_not_approved_internal_admin_gate_only"
    assert gate["delivery_publication_verdict"] == DELIVERY_PUBLICATION_VERDICT
    assert AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM in gate[
        "safe_to_claim"
    ]
    assert AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_SAFE_CLAIM in gate[
        "safe_to_claim"
    ]


def test_gate_preserves_approved_text_boundary_without_customer_exposure():
    gate = build_aas_single_boundary_delivery_publication_gate()
    snapshot = gate["approved_text_boundary_snapshot"]

    assert snapshot == {
        "selected_boundary_key": "compliance_desk",
        "family_id": "compliance_desk_as_a_service",
        "family_label": "Compliance Desk as a Service",
        "offer_id": "visible_posting_notice_compliance_snapshot",
        "approved_text_boundary": APPROVED_TEXT_BOUNDARY,
        "exact_approved_text": EXACT_APPROVED_TEXT,
        "approved_text_fields": APPROVED_TEXT_FIELDS,
        "human_operator_approval_recorded": True,
        "selected_boundary_approved": True,
        "customer_delivery_authorized_by_snapshot": False,
        "publication_authorized_by_snapshot": False,
    }
    assert gate["authorized_delivery_path"] == APPROVAL_RECORD_ALLOWED_DELIVERY_PATH
    assert gate["authorized_delivery_path_authorized"] is False


def test_delivery_publication_checks_are_internal_hold_only():
    gate = build_aas_single_boundary_delivery_publication_gate()

    assert [item["check"] for item in gate["delivery_publication_checks"]] == (
        REQUIRED_DELIVERY_PUBLICATION_CHECKS
    )
    for item in gate["delivery_publication_checks"]:
        assert item["approval_granted"] is False
        assert item["customer_delivery_allowed"] is False
        assert item["publication_allowed"] is False
    assert gate["delivery_publication_checks"][0]["structural_check_passed"] is True
    assert gate["delivery_publication_checks"][3]["structural_check_passed"] is False


def test_redaction_and_domain_authority_checks_must_rerun_at_delivery_time():
    gate = build_aas_single_boundary_delivery_publication_gate()
    reverification = gate["delivery_time_reverification"]

    assert [item["check"] for item in reverification] == [
        *REQUIRED_REDACTION_CHECKS,
        "domain_authority_claims_reverified_at_delivery_time",
    ]
    for item in reverification:
        assert item["rerun_required_at_delivery_time"] is True
        assert item["passed_for_delivery"] is False
        assert item["authorizes_delivery_or_publication"] is False
    assert reverification[-1]["source_record_passed"] is False


def test_path_channels_route_catalog_dispatch_reputation_runtime_gps_legal_and_worker_flags_false():
    gate = build_aas_single_boundary_delivery_publication_gate()

    assert gate["authorized_delivery_path_detail"] == {
        "path": APPROVAL_RECORD_ALLOWED_DELIVERY_PATH,
        "path_authorized_for_customer_delivery": False,
        "customer_delivery_allowed": False,
        "publication_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "controlled_pilot_allowed": False,
        "operator_queue_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
        "domain_authority_claims_allowed": False,
    }
    assert gate["delivery_channel_gate"] == {
        "internal_admin_only": True,
        "customer_email_allowed": False,
        "customer_dashboard_allowed": False,
        "public_catalog_allowed": False,
        "api_route_allowed": False,
        "worker_visible_instruction_allowed": False,
    }
    for container in [
        "route_catalog_pilot_queue_dispatch_gate",
        "reputation_runtime_gps_legal_worker_gate",
    ]:
        assert all(value is False for value in gate[container].values())
    for flag in DELIVERY_PUBLICATION_FALSE_FLAGS:
        assert gate[flag] is False


def test_claim_boundaries_preserve_blocked_claims():
    gate = build_aas_single_boundary_delivery_publication_gate()
    key_order = list(gate.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert not set(gate["safe_to_claim"]) & set(gate["do_not_claim_yet"])
    assert gate["still_blocked_claims"] == gate["do_not_claim_yet"]
    for claim in DELIVERY_PUBLICATION_BLOCKED_CLAIMS:
        assert claim in gate["do_not_claim_yet"]
        assert claim not in gate["safe_to_claim"]
    assert "publication_approved" not in gate["safe_to_claim"]
    assert "customer_delivery_approved" not in gate["safe_to_claim"]
    assert "dispatch_ready" not in gate["safe_to_claim"]


def test_write_gate_persists_valid_artifact(tmp_path):
    seed_source_record(tmp_path)

    path = write_aas_single_boundary_delivery_publication_gate(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_FILENAME
    assert load_aas_single_boundary_delivery_publication_gate(
        artifact_dir=tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_source_delivery_promotion_fails_closed():
    record = build_aas_single_boundary_human_operator_approval_record()
    record = copy.deepcopy(record)
    record["customer_delivery_approved"] = True

    with pytest.raises(CityOpsContractError, match="source promoted false flag"):
        build_aas_single_boundary_delivery_publication_gate(source_record=record)


def test_source_forbidden_safe_claim_fails_closed():
    record = build_aas_single_boundary_human_operator_approval_record()
    record = copy.deepcopy(record)
    record["safe_to_claim"].append("publication_approved")

    with pytest.raises(CityOpsContractError, match="source forbidden safe claims"):
        build_aas_single_boundary_delivery_publication_gate(source_record=record)


def test_loader_fails_closed_on_authorized_delivery_path_flip(tmp_path):
    seed_source_record(tmp_path)
    gate = build_aas_single_boundary_delivery_publication_gate(artifact_dir=tmp_path)
    gate["authorized_delivery_path_authorized"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted false flag"):
        load_aas_single_boundary_delivery_publication_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_delivery_time_redaction_pass(tmp_path):
    seed_source_record(tmp_path)
    gate = build_aas_single_boundary_delivery_publication_gate(artifact_dir=tmp_path)
    gate["delivery_time_reverification"][0]["passed_for_delivery"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="passed delivery check"):
        load_aas_single_boundary_delivery_publication_gate(artifact_dir=tmp_path)


def test_loader_fails_closed_on_publication_allowed_detail_flip(tmp_path):
    seed_source_record(tmp_path)
    gate = build_aas_single_boundary_delivery_publication_gate(artifact_dir=tmp_path)
    gate["authorized_delivery_path_detail"]["publication_allowed"] = True
    (tmp_path / AAS_SINGLE_BOUNDARY_DELIVERY_PUBLICATION_GATE_FILENAME).write_text(
        json.dumps(gate), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted delivery detail"):
        load_aas_single_boundary_delivery_publication_gate(artifact_dir=tmp_path)
