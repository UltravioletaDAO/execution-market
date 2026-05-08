import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_offer_fixture_specs import (
    EXPECTED_PROOF_STATUS_BY_OFFER,
    REQUIRED_BLOCKED_CLAIMS,
    REQUIRED_OFFER_IDS,
)
from mcp_server.city_ops.phase1_review_output_schemas import (
    PHASE1_REVIEW_OUTPUT_SCHEMA_BUNDLE_FILENAME,
    PHASE1_REVIEW_OUTPUT_SCHEMA_BUNDLE_SCHEMA,
    PHASE1_REVIEW_OUTPUT_SCHEMA_SAFE_CLAIM,
    REQUIRED_SCHEMA_GUARDRAILS,
    REQUIRED_SHARED_REVIEW_OUTPUT_FIELDS,
    build_phase1_review_output_schema_bundle,
    validate_phase1_review_output,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
SPEC_DIR = FIXTURES / "phase1_offer_fixture_specs"


def read_bundle_fixture() -> dict:
    with (SPEC_DIR / PHASE1_REVIEW_OUTPUT_SCHEMA_BUNDLE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def load_specs() -> dict[str, dict]:
    specs = {}
    for offer_id in REQUIRED_OFFER_IDS:
        with (SPEC_DIR / f"{offer_id}.json").open("r", encoding="utf-8") as fh:
            specs[offer_id] = json.load(fh)
    return specs


def sample_output_for(offer_id: str) -> dict:
    bundle = build_phase1_review_output_schema_bundle()
    schema = bundle["schemas_by_offer"][offer_id]
    output = {
        "offer": offer_id,
        "outcome_status": schema["enum_constraints"]["outcome_status"][0],
        "source_type": schema["enum_constraints"]["source_type"][0],
        "evidence_summary": ["Operator-reviewed fixture note."],
        "operator_review_status": "reviewed",
        "structured_next_step": "Review the scoped operational next step before dispatching any follow-on task.",
        "follow_on_task_trigger": None,
        "proof_status_label": EXPECTED_PROOF_STATUS_BY_OFFER[offer_id],
        "forbidden_claims_preserved": True,
    }
    for field in schema["required_fields"]:
        output.setdefault(field, f"sample_{field}")
    # Keep nullable follow-on trigger nullable even if it was added by setdefault.
    output["follow_on_task_trigger"] = None
    return output


def test_phase1_review_output_schema_bundle_matches_fixture():
    bundle = build_phase1_review_output_schema_bundle()

    assert bundle == read_bundle_fixture()
    assert bundle["schema"] == PHASE1_REVIEW_OUTPUT_SCHEMA_BUNDLE_SCHEMA
    assert bundle["offer_ids"] == REQUIRED_OFFER_IDS
    assert PHASE1_REVIEW_OUTPUT_SCHEMA_SAFE_CLAIM in bundle["safe_to_claim"]
    assert bundle["commercial_scope"]["operator_review_required"] is True
    assert bundle["commercial_scope"]["automation_claim_allowed"] is False
    assert bundle["commercial_scope"]["customer_copy_changed"] is False
    assert bundle["commercial_scope"]["live_transport_claim_allowed"] is False


@pytest.mark.parametrize("offer_id", REQUIRED_OFFER_IDS)
def test_each_offer_schema_preserves_reviewed_output_and_guardrails(offer_id):
    bundle = build_phase1_review_output_schema_bundle()
    schema = bundle["schemas_by_offer"][offer_id]

    for field in REQUIRED_SHARED_REVIEW_OUTPUT_FIELDS:
        assert field in schema["required_fields"]
    for guardrail in REQUIRED_SCHEMA_GUARDRAILS:
        assert guardrail in schema["guardrails"]
    assert schema["operator_review_required"] is True
    assert schema["automation_claim_allowed"] is False
    assert schema["customer_copy_changed"] is False
    assert schema["enum_constraints"]["operator_review_status"] == ["reviewed"]
    assert schema["enum_constraints"]["proof_status_label"] == [
        EXPECTED_PROOF_STATUS_BY_OFFER[offer_id]
    ]
    assert schema["forbidden_customer_claims"] == REQUIRED_BLOCKED_CLAIMS


@pytest.mark.parametrize("offer_id", REQUIRED_OFFER_IDS)
def test_valid_reviewed_output_passes_offer_schema(offer_id):
    result = validate_phase1_review_output(offer_id, sample_output_for(offer_id))

    assert result["offer_id"] == offer_id
    assert result["status"] == "passed"
    assert result["schema_id"] == (
        f"caas_phase1_{offer_id}_review_output_schema_v0"
    )


def test_reviewed_output_rejects_unreviewed_status():
    output = sample_output_for("counter_reality_check")
    output["operator_review_status"] = "pending"

    with pytest.raises(CityOpsContractError, match="operator_review_status"):
        validate_phase1_review_output("counter_reality_check", output)


def test_reviewed_output_rejects_broadened_proof_label():
    output = sample_output_for("packet_submission_attempt")
    output["proof_status_label"] = "local_anchor_supported"

    with pytest.raises(CityOpsContractError, match="proof_status_label"):
        validate_phase1_review_output("packet_submission_attempt", output)


def test_reviewed_output_rejects_missing_forbidden_claim_preservation():
    output = sample_output_for("posting_compliance_check")
    output["forbidden_claims_preserved"] = False

    with pytest.raises(CityOpsContractError, match="forbidden_claims_preserved"):
        validate_phase1_review_output("posting_compliance_check", output)


def test_schema_bundle_rejects_dropped_spec_required_field():
    specs = load_specs()
    specs["counter_reality_check"] = copy.deepcopy(specs["counter_reality_check"])
    specs["counter_reality_check"]["customer_output_schema_draft"][
        "required_fields"
    ].append("new_offer_specific_review_field")

    # Simulate a stale generated schema that did not carry the new spec field by
    # breaking the spec itself before the bundle can normalize it.
    specs["counter_reality_check"]["customer_output_schema_draft"][
        "required_fields"
    ].remove("source_type")

    with pytest.raises(CityOpsContractError, match="reviewed output fields"):
        build_phase1_review_output_schema_bundle(specs=specs)
