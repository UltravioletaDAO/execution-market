"""Internal/admin AAS pattern-recognition multiplier ladder.

This 4 AM slice consumes the package-family hold selector and turns the prompt's
pattern-recognition questions into a deterministic, read-only multiplier ladder.
It is not an operator answer, approval record, answer receipt, customer/worker/
public copy, cross-project integration, route, queue, dispatch, runtime mutation,
reputation event, payment/production change, location/private-context release,
authority claim, or stopped-project bridge.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_package_family_hold_selector import (
    AAS_PACKAGE_FAMILY_HOLD_SELECTOR_FILENAME,
    AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SAFE_CLAIM,
    AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SCHEMA,
    AAS_PACKAGE_FAMILY_HOLD_SELECTOR_STATUS,
    PACKAGE_FAMILY_HOLD_SELECTOR_BLOCKED_CLAIMS,
    RECOMMENDED_BOUNDED_LOCAL_COUNT_VALUE,
    load_aas_package_family_hold_selector,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_PATTERN_MULTIPLIER_LADDER_SCHEMA = "city_ops.aas_pattern_multiplier_ladder.v1"
AAS_PATTERN_MULTIPLIER_LADDER_FILENAME = "aas_pattern_multiplier_ladder.json"
AAS_PATTERN_MULTIPLIER_LADDER_SAFE_CLAIM = (
    "internal_admin_aas_pattern_multiplier_ladder_landed"
)
AAS_PATTERN_MULTIPLIER_LADDER_ID = (
    "execution_market.aas.pattern_multiplier_ladder.2026_06_14_0400"
)
AAS_PATTERN_MULTIPLIER_LADDER_STATUS = (
    "internal_admin_pattern_map_no_answer_no_approval_no_runtime_dispatch_payment_or_stopped_project_work"
)

FALSE_FLAGS = {
    "ladder_records_operator_answer": False,
    "ladder_records_operator_approval": False,
    "ladder_creates_answer_receipt": False,
    "ladder_selects_future_answer": False,
    "ladder_approves_product_exposure": False,
    "ladder_authorizes_collection_site_access_or_event_access": False,
    "ladder_creates_customer_public_or_worker_copy": False,
    "ladder_creates_catalog_pricing_quote_route_queue_or_dispatch": False,
    "ladder_creates_worker_instruction": False,
    "ladder_mutates_memory_acontext_irc_runtime_or_session_manager": False,
    "ladder_emits_reputation_or_worker_skill_dna": False,
    "ladder_reverifies_payment_production_or_chain_state": False,
    "ladder_releases_exact_gps_raw_metadata_private_context_or_pii": False,
    "ladder_grants_domain_legal_safety_repair_insurance_permit_or_sla_authority": False,
    "ladder_publishes_worker_copyable_doctrine": False,
    "ladder_integrates_or_expands_stopped_projects": False,
}

PATTERN_ROWS = [
    {
        "pattern_code": "memory_digest_preservation",
        "observed_pattern": "reviewed safe_claims, blocked_claims, posture, and source digests are the reusable unit",
        "multiplier_effect_if_proven_later": "every later AAS package can inherit the same anti-drift evidence boundary instead of rewriting policy text",
        "safe_now": "carry digest pointers and claim boundaries only",
        "blocked_until_gate": "no durable memory write, live Acontext mutation, or customer-facing learning claim without a reviewed result and operator approval path",
        "scales_best_when": "artifact digests are stable and every derived packet rejects safe/blocked claim overlap",
    },
    {
        "pattern_code": "irc_handoff_without_route_mutation",
        "observed_pattern": "coordination value comes from compact handoff capsules, not from assigning work while truth is missing",
        "multiplier_effect_if_proven_later": "agents can resume AAS planning with fewer stale-context errors while the operator gate remains intact",
        "safe_now": "summarize posture, next gate, and stopped-project firewall as read-only handoff fields",
        "blocked_until_gate": "no IRC session-manager mutation, routing, queue creation, or agent assignment from this ladder",
        "scales_best_when": "handoffs include exactly one next gate and explicitly say hold when no answer exists",
    },
    {
        "pattern_code": "stale_cron_firewall",
        "observed_pattern": "DREAM-PRIORITIES is the active selector and old cron payloads are noisy inputs",
        "multiplier_effect_if_proven_later": "night work stops leaking effort into deprecated tracks and compounds the current AAS lane",
        "safe_now": "treat stopped-project mentions as inputs to reject, not as backlog",
        "blocked_until_gate": "no AutoJob, Frontier Academy, KK v2, or KarmaCadabra v2 analysis, edits, tests, integrations, or publication",
        "scales_best_when": "every dream slice cites the priority source and carries explicit false firewall flags",
    },
    {
        "pattern_code": "single_answer_receipt_gate",
        "observed_pattern": "Bounded Local Count has enough fixture grammar; the missing multiplier is one explicit answer receipt",
        "multiplier_effect_if_proven_later": "one digest-backed value can unlock downstream validation without turning all package menus into launch claims",
        "safe_now": "name the recommended future value without selecting it",
        "blocked_until_gate": "no selected value, customer copy, collection, route, dispatch, reputation, payment, or runtime movement before receipt",
        "scales_best_when": "the answer receipt consumes the hold selector digest and records the operator source separately",
    },
    {
        "pattern_code": "concept_menu_as_option_space",
        "observed_pattern": "Visible Asset State and Pre-Event Blocker menus are useful as option grammar, not proof of readiness",
        "multiplier_effect_if_proven_later": "new AAS families can be compared by missing truth family before any expensive implementation work",
        "safe_now": "compare state/check codes, missing truth families, and forbidden promotions only",
        "blocked_until_gate": "no asset class, event type, collection method, field access, permit/security/vendor decision, repair, SLA, or safety claim",
        "scales_best_when": "menus keep every option adjacent to a missing truth family and forbidden promotion",
    },
    {
        "pattern_code": "observability_of_restraint",
        "observed_pattern": "the highest-signal metric tonight is whether readiness flags stay false under attractive integration language",
        "multiplier_effect_if_proven_later": "operators can see whether agents preserved trust boundaries before any public product motion",
        "safe_now": "track hold discipline, firewall discipline, and one-next-gate clarity",
        "blocked_until_gate": "no public dashboard metric, payment/chain health claim, production maturity claim, or worker skill DNA movement",
        "scales_best_when": "tests intentionally mutate readiness flags and fail closed",
    },
]

MULTIPLIER_LADDER_BLOCKED_CLAIMS = [
    *PACKAGE_FAMILY_HOLD_SELECTOR_BLOCKED_CLAIMS,
    "pattern_multiplier_ladder_records_operator_answer",
    "pattern_multiplier_ladder_records_operator_approval",
    "pattern_multiplier_ladder_creates_answer_receipt",
    "pattern_multiplier_ladder_selects_future_answer",
    "pattern_multiplier_ladder_treats_pattern_as_authorization",
    "pattern_multiplier_ladder_approves_product_exposure",
    "pattern_multiplier_ladder_authorizes_collection_site_access_or_event_access",
    "pattern_multiplier_ladder_creates_customer_public_or_worker_copy",
    "pattern_multiplier_ladder_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "pattern_multiplier_ladder_creates_worker_instruction",
    "pattern_multiplier_ladder_mutates_memory_acontext_irc_runtime_or_session_manager",
    "pattern_multiplier_ladder_emits_erc8004_reputation_or_worker_skill_dna",
    "pattern_multiplier_ladder_reverifies_payment_production_or_chain_state",
    "pattern_multiplier_ladder_releases_exact_gps_raw_metadata_private_context_or_pii",
    "pattern_multiplier_ladder_grants_domain_legal_safety_repair_insurance_permit_or_sla_authority",
    "pattern_multiplier_ladder_publishes_worker_copyable_doctrine",
    "pattern_multiplier_ladder_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(MULTIPLIER_LADDER_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "future_answer_selected",
    "collection_authorized",
    "field_visit_authorized",
    "event_site_access_authorized",
    "customer_copy_ready",
    "public_catalog_ready",
    "pricing_ready",
    "queue_ready",
    "dispatch_ready",
    "worker_instruction_ready",
    "memory_mutation_ready",
    "runtime_parity_proven",
    "live_acontext_ready",
    "irc_session_manager_mutated",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "private_context_release_ready",
    "pii_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "karmacadabra_v2_ready",
}


def _stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_aas_pattern_multiplier_ladder(
    *,
    artifact_dir: str | Path | None = None,
    hold_selector: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic 4 AM pattern-recognition multiplier ladder."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    selector = hold_selector or load_aas_package_family_hold_selector(
        artifact_dir=source_dir
    )
    _assert_hold_selector(selector)

    safe_to_claim = _dedupe(
        [
            *selector["claim_boundaries"]["safe_to_claim"],
            AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SAFE_CLAIM,
            AAS_PATTERN_MULTIPLIER_LADDER_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *selector["claim_boundaries"]["do_not_claim_yet"],
            *MULTIPLIER_LADDER_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    ladder: dict[str, Any] = {
        "schema": AAS_PATTERN_MULTIPLIER_LADDER_SCHEMA,
        "ladder_id": AAS_PATTERN_MULTIPLIER_LADDER_ID,
        "ladder_status": AAS_PATTERN_MULTIPLIER_LADDER_STATUS,
        "source_selector": {
            "file": AAS_PACKAGE_FAMILY_HOLD_SELECTOR_FILENAME,
            "schema": selector["schema"],
            "status": selector["selector_status"],
            "safe_claim": AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SAFE_CLAIM,
            "digest_sha256": _stable_digest(selector),
            "recommended_value_if_human_moves": RECOMMENDED_BOUNDED_LOCAL_COUNT_VALUE,
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service internal/admin planning",
            "source_precedence": "dream_priorities_wins_over_stale_cron_payload",
            "stopped_project_firewall": {
                "autojob_work_allowed": False,
                "frontier_academy_work_allowed": False,
                "kk_v2_work_allowed": False,
                "karmacadabra_v2_work_allowed": False,
            },
        },
        "pattern_multiplier_rows": [dict(row) for row in PATTERN_ROWS],
        "late_night_synthesis": {
            "best_scaling_pattern": "digest_backed_read_only_handoffs_with_one_explicit_next_gate",
            "highest_value_connection": "memory_digest_preservation_plus_stale_cron_firewall_plus_answer_receipt_gate",
            "why_it_compounds": "agents preserve context and boundaries across sessions without turning planning depth into authorization",
            "next_safe_action_if_no_operator_answer": "hold_pause_aas_proof_layering_and_do_not_add_more_package_menus",
            "next_safe_action_if_operator_answer_arrives": "create_one_separate_digest_backed_bounded_local_count_answer_receipt",
        },
        "current_operator_state": {
            "explicit_operator_answer_available": False,
            "operator_approval_recorded": False,
            "answer_receipt_created": False,
            "selected_value": None,
            "selected_posture_now": "pause_aas_proof_layering",
        },
        "readiness": {
            "pattern_multiplier_ladder_landed": True,
            "source_selector_verified": True,
            "pattern_rows_are_read_only": True,
            "single_next_gate_preserved": True,
            **FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "ladder_digest_sha256": "",
    }
    ladder["ladder_digest_sha256"] = _stable_digest(
        {k: v for k, v in ladder.items() if k != "ladder_digest_sha256"}
    )
    _assert_aas_pattern_multiplier_ladder(ladder, hold_selector=selector)
    return ladder


def _assert_hold_selector(selector: dict[str, Any]) -> None:
    if selector.get("schema") != AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SCHEMA:
        raise CityOpsContractError("AAS pattern multiplier ladder source selector schema drift")
    if selector.get("selector_status") != AAS_PACKAGE_FAMILY_HOLD_SELECTOR_STATUS:
        raise CityOpsContractError("AAS pattern multiplier ladder source selector status drift")
    operator = selector.get("current_operator_state", {})
    if operator.get("explicit_operator_answer_available") is not False:
        raise CityOpsContractError("AAS pattern multiplier ladder source recorded operator answer")
    if operator.get("operator_approval_recorded") is not False:
        raise CityOpsContractError("AAS pattern multiplier ladder source recorded operator approval")
    if operator.get("answer_receipt_created") is not False:
        raise CityOpsContractError("AAS pattern multiplier ladder source created answer receipt")
    if operator.get("selected_value") is not None:
        raise CityOpsContractError("AAS pattern multiplier ladder source selected a value")
    if operator.get("selected_posture_now") != "pause_aas_proof_layering":
        raise CityOpsContractError("AAS pattern multiplier ladder source posture drift")

    firewall = selector.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS pattern multiplier ladder source allowed {key}")


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"AAS pattern multiplier ladder claim overlap: {sorted(overlap)}"
        )
    forbidden_safe = set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS pattern multiplier ladder forbidden safe claims: {sorted(forbidden_safe)}"
        )


def _assert_aas_pattern_multiplier_ladder(
    ladder: dict[str, Any], *, hold_selector: dict[str, Any]
) -> None:
    _assert_hold_selector(hold_selector)
    if ladder.get("schema") != AAS_PATTERN_MULTIPLIER_LADDER_SCHEMA:
        raise CityOpsContractError("AAS pattern multiplier ladder schema drift")
    if ladder.get("ladder_status") != AAS_PATTERN_MULTIPLIER_LADDER_STATUS:
        raise CityOpsContractError("AAS pattern multiplier ladder status drift")
    if ladder.get("source_selector", {}).get("digest_sha256") != _stable_digest(hold_selector):
        raise CityOpsContractError("AAS pattern multiplier ladder source digest drift")
    if ladder.get("pattern_multiplier_rows") != PATTERN_ROWS:
        raise CityOpsContractError("AAS pattern multiplier ladder row drift")

    operator = ladder.get("current_operator_state", {})
    if operator.get("explicit_operator_answer_available") is not False:
        raise CityOpsContractError("AAS pattern multiplier ladder recorded operator answer")
    if operator.get("operator_approval_recorded") is not False:
        raise CityOpsContractError("AAS pattern multiplier ladder recorded operator approval")
    if operator.get("answer_receipt_created") is not False:
        raise CityOpsContractError("AAS pattern multiplier ladder created answer receipt")
    if operator.get("selected_value") is not None:
        raise CityOpsContractError("AAS pattern multiplier ladder selected a value")
    if operator.get("selected_posture_now") != "pause_aas_proof_layering":
        raise CityOpsContractError("AAS pattern multiplier ladder posture drift")

    readiness = ladder.get("readiness", {})
    for key, expected in FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS pattern multiplier ladder promoted {key}")

    firewall = ladder.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS pattern multiplier ladder allowed {key}")

    safe = set(ladder.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(ladder.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_PATTERN_MULTIPLIER_LADDER_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS pattern multiplier ladder safe claim missing")
    missing = set(MULTIPLIER_LADDER_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS pattern multiplier ladder missing blocked claims: {sorted(missing)}"
        )
    _assert_no_claim_overlap(list(safe), list(blocked))

    digest = ladder.get("ladder_digest_sha256")
    expected = _stable_digest({k: v for k, v in ladder.items() if k != "ladder_digest_sha256"})
    if digest != expected:
        raise CityOpsContractError("AAS pattern multiplier ladder digest drift")


def write_aas_pattern_multiplier_ladder(*, artifact_dir: str | Path | None = None) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    ladder = build_aas_pattern_multiplier_ladder(artifact_dir=target_dir)
    target_path = target_dir / AAS_PATTERN_MULTIPLIER_LADDER_FILENAME
    target_path.write_text(
        json.dumps(ladder, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target_path


def load_aas_pattern_multiplier_ladder(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_PATTERN_MULTIPLIER_LADDER_FILENAME
    ladder = json.loads(path.read_text(encoding="utf-8"))
    selector = load_aas_package_family_hold_selector(artifact_dir=source_dir)
    _assert_aas_pattern_multiplier_ladder(ladder, hold_selector=selector)
    return ladder
