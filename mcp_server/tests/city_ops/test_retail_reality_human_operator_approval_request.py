import copy
import hashlib
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.retail_reality_human_operator_approval_request import (
    APPROVAL_REQUEST_STATUS,
    AUTHORIZED_DELIVERY_PATH,
    REDACTION_AND_AUTHORITY_REQUIREMENTS,
    REQUEST_BLOCKED_CLAIMS,
    REQUEST_ID,
    REQUEST_READINESS_FALSE_FLAGS,
    REQUIRED_PRE_APPROVAL_CHECKS,
    RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME,
    RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM,
    RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA,
    SELECTED_TEXT_BOUNDARY_KEY,
    build_retail_reality_human_operator_approval_request,
    load_retail_reality_human_operator_approval_request,
    write_retail_reality_human_operator_approval_request,
)
from mcp_server.city_ops.retail_reality_internal_sample_output import (
    RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM,
    build_retail_reality_internal_sample_output,
)
from mcp_server.city_ops.retail_reality_sample_output_review_decision import (
    RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    build_retail_reality_sample_output_review_decision,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_request() -> dict:
    with (ARTIFACT_DIR / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_retail_reality_human_operator_approval_request_matches_persisted_artifact():
    request = build_retail_reality_human_operator_approval_request()

    assert request == read_request()
    assert load_retail_reality_human_operator_approval_request() == request
    assert request["schema"] == RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SCHEMA
    assert request["request_id"] == REQUEST_ID
    assert request["scope"] == "internal_admin_retail_reality_human_operator_approval_request_only"
    assert request["approval_request_status"] == APPROVAL_REQUEST_STATUS
    assert RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_SAFE_CLAIM in request["safe_to_claim"]
    assert RETAIL_REALITY_INTERNAL_SAMPLE_OUTPUT_SAFE_CLAIM in request["safe_to_claim"]
    assert RETAIL_REALITY_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM in request["safe_to_claim"]


def test_approval_request_advances_ladder_but_records_no_approval():
    request = build_retail_reality_human_operator_approval_request()

    assert request["ladder_boundary"]["covered_steps"][-1] == "human_operator_approval_request"
    assert request["ladder_boundary"]["next_required_steps_before_promotion"] == [
        "separate_human_operator_approval_record_if_authorized"
    ]
    assert request["ladder_boundary"]["promotion_allowed"] is False
    assert request["human_operator_approval_recorded"] is False
    assert request["selected_text_boundary_approved"] is False
    assert request["selected_sample_text_approved_for_customer"] is False
    assert request["authorized_delivery_path_recorded"] is False
    assert request["operator_publish_approval"] is False
    assert request["customer_delivery_approval"] is False


def test_selected_boundary_is_exact_digest_bound_internal_sample_text_only():
    sample = build_retail_reality_internal_sample_output()
    request = build_retail_reality_human_operator_approval_request(source_sample_output=sample)
    boundary = request["selected_text_boundary"]
    expected_digest = hashlib.sha256(
        json.dumps(
            sample["sample_output"]["field_values"],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    assert request["selected_text_boundary_count"] == 1
    assert boundary["key"] == SELECTED_TEXT_BOUNDARY_KEY
    assert boundary["source_sample_output_id"] == sample["sample_output_id"]
    assert boundary["candidate_text_values"] == sample["sample_output"]["field_values"]
    assert boundary["candidate_text_digest_sha256"] == expected_digest
    assert boundary["selected_text_boundary_approved"] is False
    assert boundary["customer_delivery_authorized_by_boundary"] is False
    assert boundary["publication_authorized_by_boundary"] is False
    assert boundary["dispatch_authorized_by_boundary"] is False
    assert boundary["reputation_authorized_by_boundary"] is False
    assert boundary["exact_gps_or_raw_metadata_authorized_by_boundary"] is False
    assert boundary["retail_authority_claims_authorized_by_boundary"] is False
    assert boundary["worker_doctrine_authorized_by_boundary"] is False
    assert all(boundary["readiness"][flag] is False for flag in REQUEST_READINESS_FALSE_FLAGS)


def test_pre_approval_redaction_and_delivery_path_stay_pending():
    request = build_retail_reality_human_operator_approval_request()

    assert [item["check"] for item in request["pre_approval_checks"]] == REQUIRED_PRE_APPROVAL_CHECKS
    for item in request["pre_approval_checks"]:
        assert item["required_before_human_approval"] is True
        assert item["passed_here"] is False
        assert item["approval_granted"] is False
        assert item["customer_delivery_allowed"] is False
        assert item["publication_allowed"] is False

    assert [item["check"] for item in request["redaction_and_authority_requirements"]] == (
        REDACTION_AND_AUTHORITY_REQUIREMENTS
    )
    for item in request["redaction_and_authority_requirements"]:
        assert item["required_before_human_approval"] is True
        assert item["passed_here"] is False
        assert item["authorizes_delivery_or_publication"] is False

    path = request["authorized_delivery_path"]
    assert path["path"] == AUTHORIZED_DELIVERY_PATH
    assert path["path_recorded"] is False
    assert path["customer_delivery_allowed"] is False
    assert path["publication_allowed"] is False
    assert path["dispatch_allowed"] is False
    assert path["reputation_attachment_allowed"] is False
    assert path["worker_doctrine_allowed"] is False


def test_request_blocks_customer_public_dispatch_reputation_runtime_and_retail_overclaims():
    request = build_retail_reality_human_operator_approval_request()
    blocked = set(request["do_not_claim_yet"])

    for claim in REQUEST_BLOCKED_CLAIMS:
        assert claim in blocked
        assert claim not in request["safe_to_claim"]
    for claim in [
        "retail_reality_customer_delivery_approved",
        "retail_reality_publication_approved",
        "retail_reality_public_route_ready",
        "retail_reality_catalog_route_ready",
        "retail_reality_pricing_or_quote_ready",
        "retail_reality_dispatch_enabled",
        "retail_reality_reputation_ready",
        "retail_reality_live_runtime_ready",
        "retail_reality_exact_gps_or_raw_metadata_release_ready",
        "retail_reality_permanent_business_status_ready",
        "retail_reality_inventory_guarantee_ready",
        "retail_reality_worker_copyable_retail_doctrine_ready",
    ]:
        assert claim in blocked
        assert claim not in request["safe_to_claim"]
    assert request["still_blocked_claims"] == request["do_not_claim_yet"]
    assert all(value is False for value in request["readiness"].values())


def test_write_retail_reality_human_operator_approval_request_persists_valid_artifact(tmp_path):
    path = write_retail_reality_human_operator_approval_request(artifact_dir=tmp_path)

    assert path == tmp_path / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME
    assert load_retail_reality_human_operator_approval_request(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_request_fails_closed_when_source_decision_stops_holding():
    sample = build_retail_reality_internal_sample_output()
    decision = copy.deepcopy(build_retail_reality_sample_output_review_decision(sample_output=sample))
    decision["review_decision"] = "approved"

    with pytest.raises(CityOpsContractError, match="source decision promoted verdict"):
        build_retail_reality_human_operator_approval_request(
            source_sample_output=sample,
            source_review_decision=decision,
        )


def test_request_fails_closed_when_source_sample_is_not_synthetic():
    sample = copy.deepcopy(build_retail_reality_internal_sample_output())
    decision = build_retail_reality_sample_output_review_decision(sample_output=sample)
    sample["sample_output"]["synthetic_fixture_only"] = False

    with pytest.raises(CityOpsContractError, match="source sample stopped being synthetic"):
        build_retail_reality_human_operator_approval_request(
            source_sample_output=sample,
            source_review_decision=decision,
        )


def test_loader_fails_closed_on_boundary_approval(tmp_path):
    request = build_retail_reality_human_operator_approval_request()
    request["selected_text_boundary"]["selected_text_boundary_approved"] = True
    (tmp_path / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="boundary promoted"):
        load_retail_reality_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    request = build_retail_reality_human_operator_approval_request()
    request["safe_to_claim"].append("retail_reality_customer_copy_ready")
    (tmp_path / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_retail_reality_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_delivery_path_promotion(tmp_path):
    request = build_retail_reality_human_operator_approval_request()
    request["authorized_delivery_path"]["customer_delivery_allowed"] = True
    (tmp_path / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="delivery path promoted"):
        load_retail_reality_human_operator_approval_request(artifact_dir=tmp_path)


def test_loader_fails_closed_on_approval_language(tmp_path):
    request = build_retail_reality_human_operator_approval_request()
    request["operator_instruction"] = "customer delivery authorized"
    (tmp_path / RETAIL_REALITY_HUMAN_OPERATOR_APPROVAL_REQUEST_FILENAME).write_text(
        json.dumps(request), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden approval fragment"):
        load_retail_reality_human_operator_approval_request(artifact_dir=tmp_path)
