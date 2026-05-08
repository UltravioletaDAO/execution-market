"""Reviewed Phase 1 CaaS proof fixtures.

This module materializes local reviewed outputs from the Phase 1 fixture specs
and review normalizer. It remains deliberately local: no customer copy is
changed, no municipal memory is written, no Acontext transport is claimed, and
no autonomous dispatch is authorized.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_offer_fixture_specs import REQUIRED_BLOCKED_CLAIMS
from .phase1_review_normalizer import normalize_phase1_review_output
from .phase1_review_output_schemas import OFFER_SPEC_DIR, validate_phase1_review_output

PHASE1_REVIEWED_FIXTURE_SCHEMA = "city_ops.phase1_reviewed_fixture.v1"
COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM = (
    "counter_reality_check_reviewed_fixture_landed"
)
POSTING_COMPLIANCE_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM = (
    "posting_compliance_check_reviewed_fixture_landed"
)
# Backward-compatible alias for the first landed reviewed fixture.
PHASE1_REVIEWED_FIXTURE_SAFE_CLAIM = COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM

COUNTER_REALITY_CHECK_FIXTURE_FILENAME = (
    "counter_reality_check_redirect_outdated_packet_001.json"
)
COUNTER_REALITY_CHECK_FIXTURE_ID = (
    "caas_phase1_counter_reality_check_redirect_outdated_packet_001"
)
POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME = (
    "posting_compliance_check_partial_legibility_001.json"
)
POSTING_COMPLIANCE_CHECK_FIXTURE_ID = (
    "caas_phase1_posting_compliance_check_partial_legibility_001"
)

DO_NOT_CLAIM_YET = [
    *REQUIRED_BLOCKED_CLAIMS,
    "live_customer_schema_contract",
    "autonomous_review_closure",
    "durable_municipal_memory_write",
    "live_acontext_readiness",
    "autonomous_dispatch_readiness",
    "multi_jurisdiction_playbook_readiness",
    "worker_copyable_municipal_doctrine",
    "guaranteed_approval",
    "legal_sufficiency",
]

FORBIDDEN_PROMOTION_FLAGS = [
    "customer_copy_changed",
    "durable_municipal_memory_write_performed",
    "acontext_write_performed",
    "autonomous_dispatch_enabled",
]


def build_counter_reality_check_reviewed_fixture() -> dict[str, Any]:
    """Build the first reviewed Counter Reality Check proof fixture.

    The fixture uses synthetic, non-jurisdiction-specific facts to exercise the
    exact closure seam: contradictory online guidance, separated evidence notes,
    operator-reviewed redirect result, and a bounded next step. It should be
    safe to replay through local validators, but not safe to promote into durable
    municipal memory or public customer copy until later replay/promotion gates
    pass.
    """

    review_form = {
        "offer": "counter_reality_check",
        "outcome_status": "redirected",
        "answer_summary": (
            "The public webpage described an outdated packet counter, but the "
            "reviewed field notes indicate the current path is a redirect to a "
            "different intake window before any packet attempt."
        ),
        "source_type": "mixed",
        "evidence_summary": [
            "Documented source: public guidance still names the legacy packet counter.",
            "Observed source: posted counter signage points intake traffic elsewhere.",
            "Staff-heard source: front-desk answer redirected the workflow before submission.",
            "Operator review: result is a redirect, not an approval path or legal conclusion.",
        ],
        "redirect_target": "current intake window / office redirect follow-through",
        "structured_next_step": (
            "Offer one bounded office_redirect_follow_through task to confirm the "
            "current intake window before any packet_submission_attempt is sold."
        ),
        "follow_on_task_trigger": "office_redirect_follow_through",
    }
    reviewed_output = normalize_phase1_review_output(review_form)
    validation = validate_phase1_review_output("counter_reality_check", reviewed_output)

    fixture = {
        "schema": PHASE1_REVIEWED_FIXTURE_SCHEMA,
        "fixture_id": COUNTER_REALITY_CHECK_FIXTURE_ID,
        "offer_id": "counter_reality_check",
        "source_fixture_spec": "counter_reality_check.json",
        "source_normalizer": "phase1_review_normalizer.py",
        "scenario": {
            "case_pattern": "contradictory_online_guidance_or_unclear_window",
            "municipal_objective": (
                "Verify whether stale public guidance matches current counter reality."
            ),
            "intake_privacy": "synthetic_non_jurisdiction_specific_example",
            "raw_transcript_used_as_authority": False,
            "unreviewed_memory_used": False,
        },
        "review_input_summary": {
            "exact_primary_question": (
                "Is this workflow still accepted at the public packet counter named online?"
            ),
            "fallback_question_if_staff_refuse": (
                "Which current intake window or next step should a bounded follow-up verify?"
            ),
            "customer_success_definition": (
                "A reviewed answer, explicit source type, redirect target if any, and one "
                "safe operational next step."
            ),
        },
        "reviewed_output": reviewed_output,
        "validation": validation,
        "promotion_gate": _local_fixture_promotion_gate(),
        "safe_to_claim": [COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM],
        "do_not_claim_yet": _unique_strings(DO_NOT_CLAIM_YET),
        "next_smallest_proof": (
            "Create the Posting Compliance Check reviewed fixture, then a non-redirect "
            "Packet Submission Attempt fixture, before promoting any Phase 1 customer copy."
        ),
    }
    _assert_reviewed_fixture_contract(
        fixture,
        expected_offer_id="counter_reality_check",
        expected_safe_claim=COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
    )
    return fixture


def build_posting_compliance_check_reviewed_fixture() -> dict[str, Any]:
    """Build the first reviewed Posting Compliance Check proof fixture.

    The fixture proves a single-site partial posting result with wide/context
    evidence, limited close/legibility evidence, an access constraint, and a
    bounded recheck trigger. It does not claim regulator acceptance, legal
    sufficiency, recurring automation, live Acontext readiness, or exact GPS / metadata exposure.
    """

    review_form = {
        "offer": "posting_compliance_check",
        "outcome_status": "verified_partial",
        "checklist_result": "partial_visibility_legibility_not_confirmed",
        "source_type": "observed",
        "evidence_summary": [
            "Observed source: wide/context evidence shows one posting visible at the expected exterior area.",
            "Observed source: close/legibility evidence could confirm header and date but not the full notice body.",
            "Observed source: access angle was constrained, so the review cannot certify complete checklist compliance.",
            "Operator review: this is a partial posting evidence result, not regulator acceptance or legal sufficiency.",
        ],
        "visibility_notes": (
            "Posting appears present from a public exterior vantage point, but glare and distance "
            "prevent full legibility confirmation without a recheck or improved angle."
        ),
        "failure_reason": (
            "Required close/legibility threshold was not fully met; exact GPS or metadata must remain out of customer copy."
        ),
        "structured_next_step": (
            "Offer one bounded posting_recheck with explicit close/legibility angle requirements; "
            "do not represent the current evidence as regulator acceptance."
        ),
        "follow_on_task_trigger": "posting_recheck",
    }
    reviewed_output = normalize_phase1_review_output(review_form)
    validation = validate_phase1_review_output("posting_compliance_check", reviewed_output)

    fixture = {
        "schema": PHASE1_REVIEWED_FIXTURE_SCHEMA,
        "fixture_id": POSTING_COMPLIANCE_CHECK_FIXTURE_ID,
        "offer_id": "posting_compliance_check",
        "source_fixture_spec": "posting_compliance_check.json",
        "source_normalizer": "phase1_review_normalizer.py",
        "scenario": {
            "case_pattern": "single_site_posting_present_but_partially_legible",
            "municipal_objective": (
                "Verify whether one scoped posting is visible and legible enough to satisfy the customer checklist."
            ),
            "intake_privacy": "synthetic_non_jurisdiction_specific_example",
            "raw_transcript_used_as_authority": False,
            "unreviewed_memory_used": False,
            "exact_gps_or_metadata_exposed": False,
        },
        "review_input_summary": {
            "required_wide_context_evidence": True,
            "required_close_legibility_evidence": True,
            "access_constraint_present": True,
            "customer_success_definition": (
                "Reviewed pass/fail/partial posting state, evidence limits, and one safe operational next step."
            ),
        },
        "reviewed_output": reviewed_output,
        "validation": validation,
        "promotion_gate": _local_fixture_promotion_gate(),
        "safe_to_claim": [POSTING_COMPLIANCE_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM],
        "do_not_claim_yet": _unique_strings(DO_NOT_CLAIM_YET),
        "next_smallest_proof": (
            "Create one non-redirect Packet Submission Attempt reviewed fixture, then add a "
            "reviewed-fixture registry/summary for operator observability."
        ),
    }
    _assert_reviewed_fixture_contract(
        fixture,
        expected_offer_id="posting_compliance_check",
        expected_safe_claim=POSTING_COMPLIANCE_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
    )
    _assert_posting_fixture_boundaries(fixture)
    return fixture


def write_counter_reality_check_reviewed_fixture(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the first reviewed Counter Reality Check proof fixture."""

    return _write_reviewed_fixture(
        build_counter_reality_check_reviewed_fixture(),
        COUNTER_REALITY_CHECK_FIXTURE_FILENAME,
        fixture_dir=fixture_dir,
    )


def write_posting_compliance_check_reviewed_fixture(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the first reviewed Posting Compliance Check proof fixture."""

    return _write_reviewed_fixture(
        build_posting_compliance_check_reviewed_fixture(),
        POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME,
        fixture_dir=fixture_dir,
    )


def load_counter_reality_check_reviewed_fixture(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted reviewed Counter Reality Check fixture."""

    fixture = _load_reviewed_fixture(COUNTER_REALITY_CHECK_FIXTURE_FILENAME, fixture_dir)
    _assert_reviewed_fixture_contract(
        fixture,
        expected_offer_id="counter_reality_check",
        expected_safe_claim=COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
    )
    return fixture


def load_posting_compliance_check_reviewed_fixture(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted reviewed Posting Compliance Check fixture."""

    fixture = _load_reviewed_fixture(POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME, fixture_dir)
    _assert_reviewed_fixture_contract(
        fixture,
        expected_offer_id="posting_compliance_check",
        expected_safe_claim=POSTING_COMPLIANCE_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM,
    )
    _assert_posting_fixture_boundaries(fixture)
    return fixture


def _write_reviewed_fixture(
    fixture: dict[str, Any], filename: str, *, fixture_dir: str | Path | None = None
) -> Path:
    base_dir = _reviewed_fixture_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / filename
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_reviewed_fixture(
    filename: str, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    path = _reviewed_fixture_dir(fixture_dir) / filename
    with path.open("r", encoding="utf-8") as fh:
        fixture = json.load(fh)
    if not isinstance(fixture, dict):
        raise CityOpsContractError(f"{filename} must contain a JSON object")
    return fixture


def _local_fixture_promotion_gate() -> dict[str, bool]:
    return {
        "ready_for_local_replay_gate": True,
        "requires_operator_review": True,
        "requires_existing_replay_promotion_gates": True,
        "customer_copy_changed": False,
        "durable_municipal_memory_write_performed": False,
        "acontext_write_performed": False,
        "autonomous_dispatch_enabled": False,
    }


def _reviewed_fixture_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _assert_reviewed_fixture_contract(
    fixture: dict[str, Any], *, expected_offer_id: str, expected_safe_claim: str
) -> None:
    if fixture.get("schema") != PHASE1_REVIEWED_FIXTURE_SCHEMA:
        raise CityOpsContractError("reviewed fixture schema mismatch")
    if fixture.get("offer_id") != expected_offer_id:
        raise CityOpsContractError(f"reviewed fixture must stay {expected_offer_id}")
    reviewed_output = fixture.get("reviewed_output")
    if not isinstance(reviewed_output, dict):
        raise CityOpsContractError("reviewed fixture missing reviewed_output")
    validate_phase1_review_output(expected_offer_id, reviewed_output)

    promotion_gate = fixture.get("promotion_gate", {})
    promoted = [
        flag for flag in FORBIDDEN_PROMOTION_FLAGS if promotion_gate.get(flag) is True
    ]
    if promoted:
        raise CityOpsContractError(f"reviewed fixture overclaims promotion flags: {promoted}")

    safe_to_claim = set(fixture.get("safe_to_claim", []))
    blocked = set(fixture.get("do_not_claim_yet", []))
    if expected_safe_claim not in safe_to_claim:
        raise CityOpsContractError(f"reviewed fixture missing safe claim: {expected_safe_claim}")
    overlap = sorted(safe_to_claim & blocked)
    if overlap:
        raise CityOpsContractError(f"reviewed fixture claim overlap: {overlap}")
    missing_blocked = [claim for claim in DO_NOT_CLAIM_YET if claim not in blocked]
    if missing_blocked:
        raise CityOpsContractError(
            f"reviewed fixture missing blocked claims: {missing_blocked}"
        )

    scenario = fixture.get("scenario", {})
    if scenario.get("raw_transcript_used_as_authority") is not False:
        raise CityOpsContractError("reviewed fixture cannot use raw transcript as authority")
    if scenario.get("unreviewed_memory_used") is not False:
        raise CityOpsContractError("reviewed fixture cannot use unreviewed memory")


def _assert_posting_fixture_boundaries(fixture: dict[str, Any]) -> None:
    reviewed_output = fixture["reviewed_output"]
    if reviewed_output.get("source_type") != "observed":
        raise CityOpsContractError("posting compliance fixture must stay observed-only")
    if reviewed_output.get("outcome_status") != "verified_partial":
        raise CityOpsContractError("posting compliance first fixture must stay partial")
    if reviewed_output.get("follow_on_task_trigger") != "posting_recheck":
        raise CityOpsContractError("posting compliance fixture must trigger bounded posting_recheck")
    scenario = fixture.get("scenario", {})
    if scenario.get("exact_gps_or_metadata_exposed") is not False:
        raise CityOpsContractError("posting compliance fixture cannot expose exact GPS or metadata")
    evidence = " ".join(reviewed_output.get("evidence_summary", []))
    forbidden_words = ["regulator acceptance is confirmed", "legally sufficient", "GPS:"]
    if any(word in evidence for word in forbidden_words):
        raise CityOpsContractError("posting compliance fixture evidence overclaims status")


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
