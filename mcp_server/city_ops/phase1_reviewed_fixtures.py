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
from .phase1_offer_fixture_specs import REQUIRED_BLOCKED_CLAIMS, REQUIRED_OFFER_IDS
from .phase1_review_normalizer import normalize_phase1_review_output
from .phase1_review_output_schemas import OFFER_SPEC_DIR, validate_phase1_review_output

PHASE1_REVIEWED_FIXTURE_SCHEMA = "city_ops.phase1_reviewed_fixture.v1"
COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM = (
    "counter_reality_check_reviewed_fixture_landed"
)
POSTING_COMPLIANCE_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM = (
    "posting_compliance_check_reviewed_fixture_landed"
)
PACKET_SUBMISSION_ATTEMPT_REVIEWED_FIXTURE_SAFE_CLAIM = (
    "packet_submission_attempt_reviewed_fixture_landed"
)
PHASE1_REVIEWED_FIXTURE_REGISTRY_SAFE_CLAIM = (
    "phase1_reviewed_fixture_registry_summary_landed"
)
# Backward-compatible alias for the first landed reviewed fixture.
PHASE1_REVIEWED_FIXTURE_SAFE_CLAIM = COUNTER_REALITY_CHECK_REVIEWED_FIXTURE_SAFE_CLAIM

PHASE1_REVIEWED_FIXTURE_REGISTRY_SCHEMA = "city_ops.phase1_reviewed_fixture_registry.v1"
PHASE1_REVIEWED_FIXTURE_REGISTRY_FILENAME = "phase1_reviewed_fixture_registry_summary.json"

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
PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME = (
    "packet_submission_attempt_rejected_fixable_non_redirect_001.json"
)
PACKET_SUBMISSION_ATTEMPT_FIXTURE_ID = (
    "caas_phase1_packet_submission_attempt_rejected_fixable_non_redirect_001"
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


def build_packet_submission_attempt_reviewed_fixture() -> dict[str, Any]:
    """Build a conservative non-redirect Packet Submission Attempt fixture.

    This fixture proves only one operator-reviewed, synthetic, single-office
    packet attempt that was rejected for a fixable preparation issue. It keeps
    source separation explicit, avoids exact GPS / metadata exposure, and does
    not claim approval, legal sufficiency, city influence, autonomous dispatch,
    live Acontext readiness, or broad filing doctrine.
    """

    review_form = {
        "offer": "packet_submission_attempt",
        "outcome_status": "rejected",
        "attempt_summary": (
            "One prepared packet was presented for intake review at a scoped office. "
            "The packet was not accepted because a supplemental checklist item was "
            "missing from the prepared set."
        ),
        "source_type": "mixed",
        "acceptance_evidence": (
            "No acceptance receipt, stamp, or confirmation was produced; absence is "
            "recorded as reviewed evidence, not as approval or denial on the merits."
        ),
        "rejection_reason": (
            "Fixable preparation issue: intake identified a missing supplemental "
            "checklist item before accepting the packet."
        ),
        "redirect_target": "not_applicable_non_redirect_attempt",
        "blocked_reason": "not_applicable_not_blocked",
        "evidence_summary": [
            "Customer-supplied source: prepared packet list and checklist were used only as intake context, not municipal authority.",
            "Observed source: one scoped intake attempt occurred; no exact GPS, address metadata, or private counter details are exposed.",
            "Staff-heard source: intake identified a missing supplemental checklist item before acceptance; no raw transcript is treated as authority.",
            "Operator review: result is a fixable non-redirect rejection, not approval, legal sufficiency, city influence, or a guaranteed resubmission path.",
        ],
        "structured_next_step": (
            "Offer one bounded rejection_diagnosis_resubmission_prep task to identify "
            "the missing checklist item and prepare a corrected packet; do not bundle "
            "or guarantee a retry, approval, legal sufficiency, or municipal fee payment."
        ),
        "follow_on_task_trigger": "rejection_diagnosis_resubmission_prep",
    }
    reviewed_output = normalize_phase1_review_output(review_form)
    validation = validate_phase1_review_output("packet_submission_attempt", reviewed_output)

    fixture = {
        "schema": PHASE1_REVIEWED_FIXTURE_SCHEMA,
        "fixture_id": PACKET_SUBMISSION_ATTEMPT_FIXTURE_ID,
        "offer_id": "packet_submission_attempt",
        "source_fixture_spec": "packet_submission_attempt.json",
        "source_normalizer": "phase1_review_normalizer.py",
        "scenario": {
            "case_pattern": "single_office_non_redirect_rejected_fixable_packet_attempt",
            "municipal_objective": (
                "Attempt one prepared packet submission and classify the reviewed outcome without implying approval."
            ),
            "intake_privacy": "synthetic_non_jurisdiction_specific_example",
            "raw_transcript_used_as_authority": False,
            "unreviewed_memory_used": False,
            "exact_gps_or_metadata_exposed": False,
            "municipal_fee_payment_performed": False,
            "non_redirect_attempt": True,
            "retry_or_resubmission_included": False,
        },
        "review_input_summary": {
            "target_office_scope": "one synthetic scoped municipal intake office",
            "documents_prepared_status": "packet_prepared_but_missing_supplemental_checklist_item",
            "receipt_stamp_or_absence_explained": True,
            "customer_success_definition": (
                "Reviewed accepted/rejected/redirected/blocked/inconclusive classification, "
                "evidence limits, and one safe operational next step."
            ),
        },
        "reviewed_output": reviewed_output,
        "validation": validation,
        "promotion_gate": _local_fixture_promotion_gate(),
        "safe_to_claim": [PACKET_SUBMISSION_ATTEMPT_REVIEWED_FIXTURE_SAFE_CLAIM],
        "do_not_claim_yet": _unique_strings(
            [
                *DO_NOT_CLAIM_YET,
                "city_relationship_or_influence",
                "unlimited_retries",
                "broad_multi_office_base_order",
                "runtime_parity_proven",
                "exact_gps_or_metadata_exposure",
            ]
        ),
        "next_smallest_proof": (
            "Use the reviewed-fixture registry/summary to count Phase 1 coverage before "
            "any customer-copy, UI, dispatch, Acontext, reputation, or worker-skill surface is promoted."
        ),
    }
    _assert_reviewed_fixture_contract(
        fixture,
        expected_offer_id="packet_submission_attempt",
        expected_safe_claim=PACKET_SUBMISSION_ATTEMPT_REVIEWED_FIXTURE_SAFE_CLAIM,
    )
    _assert_packet_submission_fixture_boundaries(fixture)
    return fixture


def build_phase1_reviewed_fixture_registry_summary(
    *, fixture_dir: str | Path | None = None, fixtures: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Summarize reviewed fixture coverage for operator observability.

    The registry is deliberately a local, read-only summary. It carries safe and
    blocked claims together so downstream operator surfaces can count proof
    coverage without strengthening customer-copy, dispatch, Acontext, runtime,
    legal, approval, or worker-copyable claims.
    """

    reviewed_fixtures = fixtures or [
        load_counter_reality_check_reviewed_fixture(fixture_dir=fixture_dir),
        load_packet_submission_attempt_reviewed_fixture(fixture_dir=fixture_dir),
        load_posting_compliance_check_reviewed_fixture(fixture_dir=fixture_dir),
    ]
    coverage_by_offer: dict[str, dict[str, Any]] = {}
    safe_claims: list[str] = [PHASE1_REVIEWED_FIXTURE_REGISTRY_SAFE_CLAIM]
    blocked_claims: list[str] = list(DO_NOT_CLAIM_YET)
    source_files_by_offer = {
        "counter_reality_check": COUNTER_REALITY_CHECK_FIXTURE_FILENAME,
        "packet_submission_attempt": PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME,
        "posting_compliance_check": POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME,
    }

    for fixture in reviewed_fixtures:
        offer_id = fixture.get("offer_id")
        if offer_id not in REQUIRED_OFFER_IDS:
            raise CityOpsContractError(f"unknown reviewed fixture offer_id: {offer_id}")
        reviewed_output = fixture["reviewed_output"]
        coverage_by_offer[offer_id] = {
            "fixture_id": fixture["fixture_id"],
            "source_file": source_files_by_offer[offer_id],
            "outcome_status": reviewed_output["outcome_status"],
            "source_type": reviewed_output["source_type"],
            "follow_on_task_trigger": reviewed_output["follow_on_task_trigger"],
            "proof_status_label": reviewed_output["proof_status_label"],
            "safe_to_claim": list(fixture.get("safe_to_claim", [])),
            "do_not_claim_yet": list(fixture.get("do_not_claim_yet", [])),
            "customer_copy_changed": fixture["promotion_gate"]["customer_copy_changed"],
            "durable_municipal_memory_write_performed": fixture["promotion_gate"][
                "durable_municipal_memory_write_performed"
            ],
            "acontext_write_performed": fixture["promotion_gate"]["acontext_write_performed"],
            "autonomous_dispatch_enabled": fixture["promotion_gate"][
                "autonomous_dispatch_enabled"
            ],
        }
        safe_claims.extend(fixture.get("safe_to_claim", []))
        blocked_claims.extend(fixture.get("do_not_claim_yet", []))

    missing_offers = [offer_id for offer_id in REQUIRED_OFFER_IDS if offer_id not in coverage_by_offer]
    if missing_offers:
        raise CityOpsContractError(f"reviewed fixture registry missing offers: {missing_offers}")

    registry = {
        "schema": PHASE1_REVIEWED_FIXTURE_REGISTRY_SCHEMA,
        "registry_id": "caas_phase1_reviewed_fixture_registry_summary_v0",
        "source_reviewed_outputs": [
            COUNTER_REALITY_CHECK_FIXTURE_FILENAME,
            PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME,
            POSTING_COMPLIANCE_CHECK_FIXTURE_FILENAME,
        ],
        "offer_ids": list(REQUIRED_OFFER_IDS),
        "total_reviewed_fixtures": len(reviewed_fixtures),
        "coverage_by_offer": coverage_by_offer,
        "safe_to_claim": _unique_strings(safe_claims),
        "do_not_claim_yet": _unique_strings(
            [
                *blocked_claims,
                "customer_copy_ready",
                "operator_ui_ready",
                "dispatch_routing_ready",
                "acontext_sink_ready",
                "erc8004_reputation_ready",
                "worker_skill_dna_ready",
                "exact_gps_or_metadata_exposure",
            ]
        ),
        "operator_observability": {
            "all_phase1_offers_have_reviewed_fixture": True,
            "safe_and_blocked_claims_travel_together": True,
            "source_files_are_local_reviewed_outputs_only": True,
            "exact_gps_or_metadata_exposed": False,
        },
        "commercial_scope": {
            "customer_copy_changed": False,
            "durable_municipal_memory_write_performed": False,
            "acontext_write_performed": False,
            "autonomous_dispatch_enabled": False,
            "legal_or_approval_claim_allowed": False,
        },
        "next_smallest_proof": (
            "Use this registry only as an operator observability source; next surface may be "
            "a read-only admin count/summary, not customer copy, dispatch automation, live "
            "Acontext, ERC-8004 reputation, or worker Skill DNA."
        ),
    }
    _assert_reviewed_fixture_registry_summary(registry)
    return registry


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


def write_packet_submission_attempt_reviewed_fixture(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the non-redirect Packet Submission Attempt reviewed fixture."""

    return _write_reviewed_fixture(
        build_packet_submission_attempt_reviewed_fixture(),
        PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME,
        fixture_dir=fixture_dir,
    )


def write_phase1_reviewed_fixture_registry_summary(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the reviewed fixture registry/summary next to reviewed outputs."""

    return _write_reviewed_fixture(
        build_phase1_reviewed_fixture_registry_summary(fixture_dir=fixture_dir),
        PHASE1_REVIEWED_FIXTURE_REGISTRY_FILENAME,
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


def load_packet_submission_attempt_reviewed_fixture(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted non-redirect Packet Submission Attempt fixture."""

    fixture = _load_reviewed_fixture(PACKET_SUBMISSION_ATTEMPT_FIXTURE_FILENAME, fixture_dir)
    _assert_reviewed_fixture_contract(
        fixture,
        expected_offer_id="packet_submission_attempt",
        expected_safe_claim=PACKET_SUBMISSION_ATTEMPT_REVIEWED_FIXTURE_SAFE_CLAIM,
    )
    _assert_packet_submission_fixture_boundaries(fixture)
    return fixture


def load_phase1_reviewed_fixture_registry_summary(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted reviewed fixture registry/summary."""

    registry = _load_reviewed_fixture(PHASE1_REVIEWED_FIXTURE_REGISTRY_FILENAME, fixture_dir)
    _assert_reviewed_fixture_registry_summary(registry)
    return registry


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


def _assert_packet_submission_fixture_boundaries(fixture: dict[str, Any]) -> None:
    reviewed_output = fixture["reviewed_output"]
    if reviewed_output.get("outcome_status") != "rejected":
        raise CityOpsContractError("packet submission fixture must stay rejected")
    if reviewed_output.get("redirect_target") != "not_applicable_non_redirect_attempt":
        raise CityOpsContractError("packet submission fixture must stay non-redirect")
    if reviewed_output.get("follow_on_task_trigger") != "rejection_diagnosis_resubmission_prep":
        raise CityOpsContractError(
            "packet submission fixture must trigger bounded rejection diagnosis"
        )
    scenario = fixture.get("scenario", {})
    if scenario.get("exact_gps_or_metadata_exposed") is not False:
        raise CityOpsContractError("packet submission fixture cannot expose exact GPS or metadata")
    if scenario.get("non_redirect_attempt") is not True:
        raise CityOpsContractError("packet submission fixture must stay non-redirect")
    if scenario.get("retry_or_resubmission_included") is not False:
        raise CityOpsContractError("packet submission fixture cannot bundle retries")
    evidence = " ".join(reviewed_output.get("evidence_summary", []))
    forbidden_phrases = [
        "approval is guaranteed",
        "legally sufficient",
        "city relationship confirmed",
        "GPS:",
        "autonomous dispatch enabled",
        "live Acontext ready",
    ]
    if any(phrase in evidence for phrase in forbidden_phrases):
        raise CityOpsContractError("packet submission fixture evidence overclaims status")


def _assert_reviewed_fixture_registry_summary(registry: dict[str, Any]) -> None:
    if registry.get("schema") != PHASE1_REVIEWED_FIXTURE_REGISTRY_SCHEMA:
        raise CityOpsContractError("reviewed fixture registry schema mismatch")
    coverage = registry.get("coverage_by_offer")
    if not isinstance(coverage, dict):
        raise CityOpsContractError("reviewed fixture registry missing coverage_by_offer")
    missing_offers = [offer_id for offer_id in REQUIRED_OFFER_IDS if offer_id not in coverage]
    if missing_offers:
        raise CityOpsContractError(f"reviewed fixture registry missing offers: {missing_offers}")
    if registry.get("total_reviewed_fixtures") != len(REQUIRED_OFFER_IDS):
        raise CityOpsContractError("reviewed fixture registry fixture count mismatch")
    if registry.get("operator_observability", {}).get("exact_gps_or_metadata_exposed") is not False:
        raise CityOpsContractError("reviewed fixture registry cannot expose exact GPS or metadata")
    scope = registry.get("commercial_scope", {})
    if any(
        scope.get(flag) is True
        for flag in [
            "customer_copy_changed",
            "durable_municipal_memory_write_performed",
            "acontext_write_performed",
            "autonomous_dispatch_enabled",
            "legal_or_approval_claim_allowed",
        ]
    ):
        raise CityOpsContractError("reviewed fixture registry overclaims commercial scope")
    safe_to_claim = set(registry.get("safe_to_claim", []))
    blocked = set(registry.get("do_not_claim_yet", []))
    overlap = sorted(safe_to_claim & blocked)
    if overlap:
        raise CityOpsContractError(f"reviewed fixture registry claim overlap: {overlap}")
    for offer_id, row in coverage.items():
        if not row.get("safe_to_claim") or not row.get("do_not_claim_yet"):
            raise CityOpsContractError(f"reviewed fixture registry row missing claims: {offer_id}")
        if row.get("customer_copy_changed") is not False:
            raise CityOpsContractError(f"reviewed fixture registry row overclaims copy: {offer_id}")


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
