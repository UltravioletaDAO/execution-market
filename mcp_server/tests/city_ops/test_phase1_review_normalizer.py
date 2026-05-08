import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_offer_fixture_specs import (
    EXPECTED_PROOF_STATUS_BY_OFFER,
    REQUIRED_OFFER_IDS,
)
from mcp_server.city_ops.phase1_review_normalizer import (
    PHASE1_REVIEW_NORMALIZER_SAFE_CLAIM,
    PHASE1_REVIEW_NORMALIZER_SUMMARY_FILENAME,
    PHASE1_REVIEW_NORMALIZER_SUMMARY_SCHEMA,
    build_phase1_review_normalizer_summary,
    normalize_phase1_review_output,
)
from mcp_server.city_ops.phase1_review_output_schemas import (
    build_phase1_review_output_schema_bundle,
    validate_phase1_review_output,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
SPEC_DIR = FIXTURES / "phase1_offer_fixture_specs"


def read_summary_fixture() -> dict:
    with (SPEC_DIR / PHASE1_REVIEW_NORMALIZER_SUMMARY_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def review_form_for(offer_id: str) -> dict:
    bundle = build_phase1_review_output_schema_bundle()
    schema = bundle["schemas_by_offer"][offer_id]
    form = {
        "offer": offer_id,
        "outcome_status": schema["enum_constraints"]["outcome_status"][0],
        "source_type": schema["enum_constraints"]["source_type"][0],
        "evidence_summary": ["Operator reviewed the submitted proof fixture."],
        "structured_next_step": "Use this reviewed result to decide whether a bounded follow-on task is needed.",
        "follow_on_task_trigger": None,
    }
    for field in schema["required_fields"]:
        form.setdefault(field, f"reviewed_{field}")
    # Let the normalizer stamp review-only fields when omitted.
    for field in (
        "operator_review_status",
        "proof_status_label",
        "forbidden_claims_preserved",
    ):
        form.pop(field, None)
    form["follow_on_task_trigger"] = None
    return form


def test_phase1_review_normalizer_summary_matches_fixture():
    summary = build_phase1_review_normalizer_summary()

    assert summary == read_summary_fixture()
    assert summary["schema"] == PHASE1_REVIEW_NORMALIZER_SUMMARY_SCHEMA
    assert PHASE1_REVIEW_NORMALIZER_SAFE_CLAIM in summary["safe_to_claim"]
    assert summary["commercial_scope"]["operator_review_required"] is True
    assert summary["commercial_scope"]["customer_copy_changed"] is False
    assert summary["commercial_scope"]["automation_claim_allowed"] is False
    assert summary["commercial_scope"]["durable_memory_write_allowed"] is False


@pytest.mark.parametrize("offer_id", REQUIRED_OFFER_IDS)
def test_normalizer_emits_valid_reviewed_output_for_each_offer(offer_id):
    reviewed_output = normalize_phase1_review_output(review_form_for(offer_id))

    assert reviewed_output["offer"] == offer_id
    assert reviewed_output["operator_review_status"] == "reviewed"
    assert reviewed_output["proof_status_label"] == EXPECTED_PROOF_STATUS_BY_OFFER[offer_id]
    assert reviewed_output["forbidden_claims_preserved"] is True
    assert validate_phase1_review_output(offer_id, reviewed_output)["status"] == "passed"


def test_normalizer_accepts_offer_id_alias_but_outputs_offer():
    form = review_form_for("counter_reality_check")
    form["offer_id"] = form.pop("offer")

    reviewed_output = normalize_phase1_review_output(form)

    assert reviewed_output["offer"] == "counter_reality_check"
    assert "offer_id" not in reviewed_output


def test_normalizer_rejects_missing_required_field():
    form = review_form_for("counter_reality_check")
    form.pop("answer_summary")

    with pytest.raises(CityOpsContractError, match="missing required fields"):
        normalize_phase1_review_output(form)


def test_normalizer_rejects_empty_required_string():
    form = review_form_for("packet_submission_attempt")
    form["attempt_summary"] = "   "

    with pytest.raises(CityOpsContractError, match="empty required fields"):
        normalize_phase1_review_output(form)


def test_normalizer_rejects_unreviewed_status():
    form = review_form_for("posting_compliance_check")
    form["operator_review_status"] = "pending"

    with pytest.raises(CityOpsContractError, match="operator_review_status"):
        normalize_phase1_review_output(form)


def test_normalizer_rejects_broadened_proof_status():
    form = review_form_for("packet_submission_attempt")
    form["proof_status_label"] = "local_anchor_supported"

    with pytest.raises(CityOpsContractError, match="proof_status_label"):
        normalize_phase1_review_output(form)


def test_normalizer_rejects_forbidden_claims_not_preserved():
    form = review_form_for("counter_reality_check")
    form["forbidden_claims_preserved"] = False

    with pytest.raises(CityOpsContractError, match="forbidden_claims_preserved"):
        normalize_phase1_review_output(form)
