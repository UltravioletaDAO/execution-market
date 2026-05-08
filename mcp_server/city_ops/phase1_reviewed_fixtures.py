"""Reviewed Phase 1 CaaS proof fixtures.

This module materializes the first local Counter Reality Check reviewed output
from the Phase 1 fixture spec and review normalizer.  It remains deliberately
local: no customer copy is changed, no municipal memory is written, no Acontext
transport is claimed, and no autonomous dispatch is authorized.
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
PHASE1_REVIEWED_FIXTURE_SAFE_CLAIM = "counter_reality_check_reviewed_fixture_landed"
COUNTER_REALITY_CHECK_FIXTURE_FILENAME = (
    "counter_reality_check_redirect_outdated_packet_001.json"
)
COUNTER_REALITY_CHECK_FIXTURE_ID = (
    "caas_phase1_counter_reality_check_redirect_outdated_packet_001"
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


def build_counter_reality_check_reviewed_fixture() -> dict[str, Any]:
    """Build the first reviewed Counter Reality Check proof fixture.

    The fixture uses synthetic, non-jurisdiction-specific facts to exercise the
    exact closure seam: contradictory online guidance, separated evidence notes,
    operator-reviewed redirect result, and a bounded next step.  It should be
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
        "promotion_gate": {
            "ready_for_local_replay_gate": True,
            "requires_operator_review": True,
            "requires_existing_replay_promotion_gates": True,
            "customer_copy_changed": False,
            "durable_municipal_memory_write_performed": False,
            "acontext_write_performed": False,
            "autonomous_dispatch_enabled": False,
        },
        "safe_to_claim": [PHASE1_REVIEWED_FIXTURE_SAFE_CLAIM],
        "do_not_claim_yet": _unique_strings(DO_NOT_CLAIM_YET),
        "next_smallest_proof": (
            "Create the Posting Compliance Check reviewed fixture, then a non-redirect "
            "Packet Submission Attempt fixture, before promoting any Phase 1 customer copy."
        ),
    }
    _assert_counter_reality_fixture_contract(fixture)
    return fixture


def write_counter_reality_check_reviewed_fixture(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the first reviewed Counter Reality Check proof fixture."""

    base_dir = _reviewed_fixture_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    fixture = build_counter_reality_check_reviewed_fixture()
    path = base_dir / COUNTER_REALITY_CHECK_FIXTURE_FILENAME
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_counter_reality_check_reviewed_fixture(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted reviewed Counter Reality Check fixture."""

    path = _reviewed_fixture_dir(fixture_dir) / COUNTER_REALITY_CHECK_FIXTURE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        fixture = json.load(fh)
    _assert_counter_reality_fixture_contract(fixture)
    return fixture


def _reviewed_fixture_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    return OFFER_SPEC_DIR / "reviewed_outputs"


def _assert_counter_reality_fixture_contract(fixture: dict[str, Any]) -> None:
    if fixture.get("schema") != PHASE1_REVIEWED_FIXTURE_SCHEMA:
        raise CityOpsContractError("reviewed fixture schema mismatch")
    if fixture.get("offer_id") != "counter_reality_check":
        raise CityOpsContractError("reviewed fixture must stay counter_reality_check")
    reviewed_output = fixture.get("reviewed_output")
    if not isinstance(reviewed_output, dict):
        raise CityOpsContractError("reviewed fixture missing reviewed_output")
    validate_phase1_review_output("counter_reality_check", reviewed_output)

    promotion_gate = fixture.get("promotion_gate", {})
    forbidden_true_flags = [
        "customer_copy_changed",
        "durable_municipal_memory_write_performed",
        "acontext_write_performed",
        "autonomous_dispatch_enabled",
    ]
    promoted = [flag for flag in forbidden_true_flags if promotion_gate.get(flag) is True]
    if promoted:
        raise CityOpsContractError(f"reviewed fixture overclaims promotion flags: {promoted}")

    safe_to_claim = set(fixture.get("safe_to_claim", []))
    blocked = set(fixture.get("do_not_claim_yet", []))
    overlap = sorted(safe_to_claim & blocked)
    if overlap:
        raise CityOpsContractError(f"reviewed fixture claim overlap: {overlap}")
    missing_blocked = [claim for claim in DO_NOT_CLAIM_YET if claim not in blocked]
    if missing_blocked:
        raise CityOpsContractError(
            f"reviewed fixture missing blocked claims: {missing_blocked}"
        )


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
