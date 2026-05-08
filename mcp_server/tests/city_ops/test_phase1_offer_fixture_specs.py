import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_offer_fixture_specs import (
    EXPECTED_PROOF_STATUS_BY_OFFER,
    PHASE1_OFFER_FIXTURE_SPEC_SAFE_CLAIM,
    PHASE1_OFFER_FIXTURE_SPEC_SUMMARY_SCHEMA,
    PHASE1_SUMMARY_FILENAME,
    REQUIRED_BLOCKED_CLAIMS,
    REQUIRED_OFFER_IDS,
    REQUIRED_REVIEWED_OUTPUT_FIELDS,
    build_phase1_offer_fixture_spec_summary,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
SPEC_DIR = FIXTURES / "phase1_offer_fixture_specs"


def read_summary_fixture() -> dict:
    with (SPEC_DIR / PHASE1_SUMMARY_FILENAME).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_specs() -> dict[str, dict]:
    specs = {}
    for offer_id in REQUIRED_OFFER_IDS:
        with (SPEC_DIR / f"{offer_id}.json").open("r", encoding="utf-8") as fh:
            specs[offer_id] = json.load(fh)
    return specs


def test_phase1_offer_fixture_spec_summary_matches_fixture():
    summary = build_phase1_offer_fixture_spec_summary()

    assert summary == read_summary_fixture()
    assert summary["schema"] == PHASE1_OFFER_FIXTURE_SPEC_SUMMARY_SCHEMA
    assert summary["spec_count"] == 3
    assert summary["offer_ids"] == REQUIRED_OFFER_IDS
    assert PHASE1_OFFER_FIXTURE_SPEC_SAFE_CLAIM in summary["claim_boundaries"][
        "safe_to_claim"
    ]
    assert summary["claim_boundaries"]["do_not_claim_yet"] == REQUIRED_BLOCKED_CLAIMS
    assert summary["commercial_scope"]["concierge_only"] is True
    assert summary["commercial_scope"]["operator_review_required"] is True
    assert summary["commercial_scope"]["automation_claim_allowed"] is False
    assert summary["commercial_scope"]["customer_copy_changed"] is False


@pytest.mark.parametrize("offer_id", REQUIRED_OFFER_IDS)
def test_each_phase1_offer_preserves_reviewed_output_contract(offer_id):
    summary = build_phase1_offer_fixture_spec_summary()

    assert summary["proof_status_by_offer"][offer_id] == EXPECTED_PROOF_STATUS_BY_OFFER[
        offer_id
    ]
    output_fields = summary["reviewed_output_fields_by_offer"][offer_id]
    for field in REQUIRED_REVIEWED_OUTPUT_FIELDS:
        assert field in output_fields


def test_summary_keeps_packet_submission_anchor_narrow():
    summary = build_phase1_offer_fixture_spec_summary()

    assert summary["proof_status_by_offer"]["packet_submission_attempt"] == (
        "local_anchor_supported_redirect_outdated_packet_only"
    )
    assert "packet_submission_attempt_non_redirect" in summary["next_fixture_order"]
    assert "worker_copyable_municipal_doctrine" in summary["claim_boundaries"][
        "do_not_claim_yet"
    ]


def test_specs_fail_when_required_blocked_claim_is_dropped():
    specs = load_specs()
    specs["counter_reality_check"] = copy.deepcopy(specs["counter_reality_check"])
    specs["counter_reality_check"]["do_not_claim_yet"].remove(
        "autonomous_dispatch_readiness"
    )

    with pytest.raises(CityOpsContractError, match="do_not_claim_yet"):
        build_phase1_offer_fixture_spec_summary(specs=specs)


def test_specs_fail_when_blocked_claim_becomes_safe():
    specs = load_specs()
    specs["posting_compliance_check"] = copy.deepcopy(specs["posting_compliance_check"])
    specs["posting_compliance_check"]["safe_to_claim"].append(
        "worker_copyable_municipal_doctrine"
    )

    with pytest.raises(CityOpsContractError, match="safe_to_claim"):
        build_phase1_offer_fixture_spec_summary(specs=specs)


def test_specs_fail_when_packet_proof_label_is_broadened():
    specs = load_specs()
    specs["packet_submission_attempt"] = copy.deepcopy(
        specs["packet_submission_attempt"]
    )
    specs["packet_submission_attempt"]["proof_status_label"] = "local_anchor_supported"

    with pytest.raises(CityOpsContractError, match="proof_status_label"):
        build_phase1_offer_fixture_spec_summary(specs=specs)


def test_specs_fail_when_reviewed_output_field_is_missing():
    specs = load_specs()
    specs["counter_reality_check"] = copy.deepcopy(specs["counter_reality_check"])
    specs["counter_reality_check"]["customer_output_schema_draft"][
        "required_fields"
    ].remove("operator_review_status")

    with pytest.raises(CityOpsContractError, match="reviewed output fields"):
        build_phase1_offer_fixture_spec_summary(specs=specs)


def test_specs_fail_when_fixture_acceptance_gate_stops_preserving_claims():
    specs = load_specs()
    specs["posting_compliance_check"] = copy.deepcopy(specs["posting_compliance_check"])
    specs["posting_compliance_check"]["fixture_acceptance_gate"][
        "preserves_safe_and_blocked_claims"
    ] = False

    with pytest.raises(CityOpsContractError, match="fixture_acceptance_gate"):
        build_phase1_offer_fixture_spec_summary(specs=specs)
