"""Internal/admin 4 AM AAS pattern-synthesis handoff.

This proof block consumes the system-integration decision-support map and turns
its non-authorizing lanes into a compact read-only handoff. It records no
operator answer or approval, selects no future answer, launches no runtime or
product exposure, emits no reputation or Worker Skill DNA, and integrates no
stopped projects.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_system_integration_decision_support_map import (
    AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME,
    AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SCHEMA,
    AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_STATUS,
    DECISION_SUPPORT_BLOCKED_CLAIMS,
    DECISION_SUPPORT_FALSE_FLAGS,
    INTEGRATION_LANES,
    load_aas_system_integration_decision_support_map,
)
from .aas_two_lane_operator_answer_schema import (
    ALLOWED_FUTURE_DECISIONS,
    DEFAULT_EFFECTIVE_DECISION,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SCHEMA = (
    "city_ops.aas_four_am_pattern_synthesis_handoff.v1"
)
AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME = (
    "aas_four_am_pattern_synthesis_handoff.json"
)
AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SAFE_CLAIM = (
    "internal_admin_aas_four_am_pattern_synthesis_handoff_landed"
)
AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_ID = (
    "execution_market.aas.four_am_pattern_synthesis_handoff.2026_06_03_0400"
)
AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_STATUS = (
    "read_only_pattern_synthesis_no_answer_no_approval_no_runtime_or_external_promotion"
)

PATTERN_SYNTHESIS_FALSE_FLAGS = {
    "handoff_records_operator_answer": False,
    "handoff_records_operator_approval": False,
    "handoff_selects_future_answer": False,
    "handoff_creates_answer_record": False,
    "handoff_treats_pattern_as_approval": False,
    "handoff_treats_question_as_answer": False,
    "handoff_approves_product_exposure": False,
    "handoff_approves_runtime_memory_wiring": False,
    "handoff_registers_runtime_adapter": False,
    "handoff_enables_runtime_adapter": False,
    "handoff_mutates_irc_session_manager": False,
    "handoff_writes_live_acontext": False,
    "handoff_retrieves_live_acontext": False,
    "handoff_enables_cross_project_autorouting": False,
    "handoff_creates_customer_copy": False,
    "handoff_creates_worker_instruction": False,
    "handoff_creates_dashboard_metric": False,
    "handoff_enables_catalog_pricing_queue_or_dispatch": False,
    "handoff_emits_erc8004_reputation": False,
    "handoff_emits_worker_skill_dna": False,
    "handoff_reverifies_payment_or_production": False,
    "handoff_releases_exact_gps_or_raw_metadata": False,
    "handoff_releases_private_context": False,
    "handoff_grants_domain_authority_claims": False,
    "handoff_publishes_worker_copyable_doctrine": False,
    "handoff_integrates_stopped_projects": False,
}

PATTERN_SYNTHESIS_BLOCKED_CLAIMS = [
    *DECISION_SUPPORT_BLOCKED_CLAIMS,
    "four_am_handoff_records_operator_answer",
    "four_am_handoff_records_operator_approval",
    "four_am_handoff_selects_future_answer",
    "four_am_handoff_treats_pattern_as_approval",
    "four_am_handoff_treats_question_as_answer",
    "four_am_handoff_creates_answer_record",
    "four_am_handoff_approves_product_exposure",
    "four_am_handoff_approves_runtime_memory_wiring",
    "four_am_handoff_registers_or_enables_runtime_adapter",
    "four_am_handoff_mutates_irc_session_manager",
    "four_am_handoff_writes_or_retrieves_live_acontext",
    "four_am_handoff_authorizes_cross_project_autorouting",
    "four_am_handoff_creates_customer_public_worker_surface",
    "four_am_handoff_creates_dashboard_or_public_metric",
    "four_am_handoff_authorizes_catalog_pricing_queue_or_dispatch",
    "four_am_handoff_emits_erc8004_reputation_or_worker_skill_dna",
    "four_am_handoff_reverifies_payment_or_production",
    "four_am_handoff_releases_exact_gps_or_raw_metadata",
    "four_am_handoff_releases_private_context",
    "four_am_handoff_grants_domain_authority_claims",
    "four_am_handoff_publishes_worker_copyable_doctrine",
    "four_am_handoff_integrates_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(PATTERN_SYNTHESIS_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "future_answer_selected",
    "answer_record_created",
    "product_exposure_approved",
    "runtime_memory_wiring_approved",
    "runtime_adapter_registered",
    "runtime_adapter_enabled",
    "irc_session_manager_mutated",
    "live_acontext_ready",
    "runtime_parity_proven",
    "cross_project_autorouting_ready",
    "customer_copy_ready",
    "dashboard_metric_ready",
    "catalog_ready",
    "pricing_ready",
    "dispatch_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "private_context_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "karmacadabra_v2_ready",
}

PATTERN_CARDS = [
    {
        "pattern": "memory_system_data_compounds_only_after_boundary_distillation",
        "connection": (
            "Daily memory, source-of-truth indexes, and decision-support maps create "
            "value only when safe and blocked claims travel together."
        ),
        "multiplier_effect_if_later_approved": (
            "Future operators inherit a smaller decision surface instead of replaying "
            "raw history."
        ),
    },
    {
        "pattern": "irc_coordination_scales_with_sanitized_handoff_invariants",
        "connection": (
            "The reusable coordination shape is the sanitized proof anchor, compact "
            "decision, review packet, source digests, and kill-switch posture."
        ),
        "multiplier_effect_if_later_approved": (
            "Agents can coordinate across sessions without exposing raw transcripts, "
            "session IDs, private context, or runtime mutation."
        ),
    },
    {
        "pattern": "cross_project_intelligence_is_a_filter_not_autopilot",
        "connection": (
            "Source-of-truth filtering prevents stale or stopped tracks from becoming "
            "launch authority while still preserving useful AAS context."
        ),
        "multiplier_effect_if_later_approved": (
            "Every future AAS lane starts from current entrypoints instead of old "
            "cron payloads or historical plans."
        ),
    },
    {
        "pattern": "agent_coordination_quality_is_claim_boundary_survival",
        "connection": (
            "The strongest coordination pattern is not more agents or more routes; it "
            "is preserving safe_to_claim beside do_not_claim_yet across handoffs."
        ),
        "multiplier_effect_if_later_approved": (
            "Product, runtime, payment, and reputation moves become auditable proof "
            "ladders instead of ambiguous enthusiasm."
        ),
    },
]


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


def _assert_source_decision_map(decision_map: dict[str, Any]) -> None:
    if decision_map.get("schema") != AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SCHEMA:
        raise CityOpsContractError("4 AM handoff source decision map schema drift")
    if decision_map.get("map_status") != AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_STATUS:
        raise CityOpsContractError("4 AM handoff source decision map status drift")
    safe = set(decision_map.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("4 AM handoff source safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"4 AM handoff source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    blocked = set(decision_map.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(DECISION_SUPPORT_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"4 AM handoff source missing blocked claims: {sorted(missing)}"
        )
    current = decision_map.get("current_no_answer_decision", {})
    if current.get("operator_answer_recorded") is not False:
        raise CityOpsContractError("4 AM handoff source recorded operator answer")
    if current.get("operator_approval_recorded") is not False:
        raise CityOpsContractError("4 AM handoff source recorded operator approval")
    if current.get("selected_future_answer") is not None:
        raise CityOpsContractError("4 AM handoff source selected future answer")
    if current.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("4 AM handoff source effective decision drift")
    readiness = decision_map.get("readiness", {})
    for key, expected in DECISION_SUPPORT_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"4 AM handoff source promoted readiness {key}")
    lanes = decision_map.get("integration_lanes", [])
    if [lane.get("lane") for lane in lanes] != [lane["lane"] for lane in INTEGRATION_LANES]:
        raise CityOpsContractError("4 AM handoff source lane drift")
    for lane in lanes:
        if lane.get("decision_support_only") is not True:
            raise CityOpsContractError("4 AM handoff source lane not support-only")
        for key in [
            "selected_by_this_map",
            "approval_granted_by_this_map",
            "runtime_or_external_promotion_allowed",
        ]:
            if lane.get(key) is not False:
                raise CityOpsContractError(f"4 AM handoff source lane promoted {key}")
    firewall = decision_map.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"4 AM handoff source allowed {key}")


def build_aas_four_am_pattern_synthesis_handoff(
    *,
    artifact_dir: str | Path | None = None,
    source_decision_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic read-only 4 AM AAS pattern handoff."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    decision_map = source_decision_map or load_aas_system_integration_decision_support_map(
        artifact_dir=source_dir
    )
    _assert_source_decision_map(decision_map)

    safe_to_claim = _dedupe(
        [
            *decision_map["claim_boundaries"]["safe_to_claim"],
            AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *decision_map["claim_boundaries"]["do_not_claim_yet"],
            *PATTERN_SYNTHESIS_BLOCKED_CLAIMS,
        ]
    )

    handoff = {
        "schema": AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SCHEMA,
        "handoff_id": AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_ID,
        "scope": "internal_admin_read_only_4am_aas_pattern_synthesis_handoff",
        "handoff_status": AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_STATUS,
        "source_policy": "consume_current_system_integration_decision_support_map_only",
        "source_decision_support_map": {
            "file": AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME,
            "schema": decision_map["schema"],
            "map_id": decision_map["map_id"],
            "safe_claim": AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_SAFE_CLAIM,
            "digest_sha256": _stable_digest(decision_map),
            "effective_decision": decision_map["current_no_answer_decision"][
                "effective_decision"
            ],
        },
        "pattern_cards": [
            {
                **card,
                "internal_admin_synthesis_only": True,
                "approved_by_this_handoff": False,
                "selected_by_this_handoff": False,
                "runtime_or_external_promotion_allowed": False,
            }
            for card in PATTERN_CARDS
        ],
        "one_question_handoff": {
            "question": "Which single future AAS path should be recorded separately?",
            "allowed_future_decisions": [
                {
                    "decision": decision,
                    "displayed_by_this_handoff": True,
                    "selected_by_this_handoff": False,
                    "requires_separate_answer_record": True,
                    "approval_granted_by_this_handoff": False,
                }
                for decision in ALLOWED_FUTURE_DECISIONS
            ],
            "default_if_no_human_answer": DEFAULT_EFFECTIVE_DECISION,
            "question_text_is_not_answer": True,
        },
        "current_no_answer_decision": {
            "operator_answer_recorded": False,
            "operator_approval_recorded": False,
            "selected_future_answer": None,
            "effective_decision": DEFAULT_EFFECTIVE_DECISION,
            "pattern_synthesis_is_approval": False,
            "handoff_is_answer_record": False,
        },
        "readiness": {
            "internal_admin_four_am_handoff_landed": True,
            "source_decision_support_map_verified": True,
            "pattern_cards_synthesized": True,
            "one_question_handoff_displayed": True,
            "default_off_non_authorizing": True,
            **PATTERN_SYNTHESIS_FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "still_blocked_claims": do_not_claim_yet,
        "stopped_project_firewall": {
            "autojob_work_allowed": False,
            "frontier_academy_work_allowed": False,
            "kk_v2_work_allowed": False,
            "karmacadabra_v2_work_allowed": False,
            "source": "DREAM-PRIORITIES.md explicit stop list",
        },
        "operator_guidance": {
            "first_read": "DREAM-PRIORITIES.md",
            "use_this_handoff_for": "internal_admin_morning_pattern_synthesis_only",
            "if_no_real_answer": "hold_both_lanes_or_pause_proof_layering",
            "if_real_answer_exists": "create_separate_two_lane_operator_answer_record_first",
            "do_not_extend_with_more_read_only_ceremony_unless_it_is_final_wrap": True,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "not_dashboard_spec": True,
        },
        "handoff_verdict": (
            "four_am_pattern_synthesis_handoff_landed_no_answer_no_approval_"
            "patterns_are_internal_admin_context_only_no_runtime_product_reputation_"
            "payment_dispatch_or_stopped_project_promotion"
        ),
    }
    _assert_aas_four_am_pattern_synthesis_handoff(handoff, source_decision_map=decision_map)
    return handoff


def _assert_aas_four_am_pattern_synthesis_handoff(
    handoff: dict[str, Any], *, source_decision_map: dict[str, Any]
) -> None:
    _assert_source_decision_map(source_decision_map)
    if handoff.get("schema") != AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SCHEMA:
        raise CityOpsContractError("4 AM handoff schema drift")
    if handoff.get("handoff_id") != AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_ID:
        raise CityOpsContractError("4 AM handoff id drift")
    if handoff.get("handoff_status") != AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_STATUS:
        raise CityOpsContractError("4 AM handoff status drift")
    source = handoff.get("source_decision_support_map", {})
    if source.get("file") != AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_FILENAME:
        raise CityOpsContractError("4 AM handoff source file drift")
    if source.get("digest_sha256") != _stable_digest(source_decision_map):
        raise CityOpsContractError("4 AM handoff source digest drift")
    if source.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("4 AM handoff source effective decision drift")

    cards = handoff.get("pattern_cards", [])
    if [card.get("pattern") for card in cards] != [card["pattern"] for card in PATTERN_CARDS]:
        raise CityOpsContractError("4 AM handoff pattern-card drift")
    for card in cards:
        if card.get("internal_admin_synthesis_only") is not True:
            raise CityOpsContractError("4 AM handoff pattern card not internal-only")
        for key in [
            "approved_by_this_handoff",
            "selected_by_this_handoff",
            "runtime_or_external_promotion_allowed",
        ]:
            if card.get(key) is not False:
                raise CityOpsContractError(f"4 AM handoff pattern card promoted {key}")

    question = handoff.get("one_question_handoff", {})
    decisions = question.get("allowed_future_decisions", [])
    if [item.get("decision") for item in decisions] != ALLOWED_FUTURE_DECISIONS:
        raise CityOpsContractError("4 AM handoff decision options drift")
    if question.get("default_if_no_human_answer") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("4 AM handoff default decision drift")
    if question.get("question_text_is_not_answer") is not True:
        raise CityOpsContractError("4 AM handoff question text became answer")
    for item in decisions:
        if item.get("displayed_by_this_handoff") is not True:
            raise CityOpsContractError("4 AM handoff decision not displayed")
        if item.get("selected_by_this_handoff") is not False:
            raise CityOpsContractError("4 AM handoff selected a decision")
        if item.get("requires_separate_answer_record") is not True:
            raise CityOpsContractError("4 AM handoff decision missing separate answer record")
        if item.get("approval_granted_by_this_handoff") is not False:
            raise CityOpsContractError("4 AM handoff granted approval")

    current = handoff.get("current_no_answer_decision", {})
    for key in [
        "operator_answer_recorded",
        "operator_approval_recorded",
        "pattern_synthesis_is_approval",
        "handoff_is_answer_record",
    ]:
        if current.get(key) is not False:
            raise CityOpsContractError(f"4 AM handoff promoted {key}")
    if current.get("selected_future_answer") is not None:
        raise CityOpsContractError("4 AM handoff selected future answer")
    if current.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("4 AM handoff effective decision drift")

    readiness = handoff.get("readiness", {})
    for key, expected in PATTERN_SYNTHESIS_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"4 AM handoff promoted readiness {key}")

    safe = set(handoff.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(handoff.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SAFE_CLAIM not in safe:
        raise CityOpsContractError("4 AM handoff safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(f"4 AM handoff forbidden safe claims: {sorted(forbidden_safe)}")
    missing_blocked = set(PATTERN_SYNTHESIS_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"4 AM handoff missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(f"4 AM handoff claim overlap: {sorted(overlap)}")
    if handoff.get("still_blocked_claims") != handoff.get("claim_boundaries", {}).get(
        "do_not_claim_yet"
    ):
        raise CityOpsContractError("4 AM handoff blocked claims drift")

    firewall = handoff.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"4 AM handoff allowed {key}")


def write_aas_four_am_pattern_synthesis_handoff(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    handoff = build_aas_four_am_pattern_synthesis_handoff(artifact_dir=target_dir)
    target_path = target_dir / AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME
    target_path.write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path


def load_aas_four_am_pattern_synthesis_handoff(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME
    handoff = json.loads(path.read_text(encoding="utf-8"))
    source_decision_map = load_aas_system_integration_decision_support_map(
        artifact_dir=source_dir
    )
    _assert_aas_four_am_pattern_synthesis_handoff(
        handoff, source_decision_map=source_decision_map
    )
    return handoff
