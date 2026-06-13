"""Internal/admin Bounded Local Count pattern compounder.

This proof block answers the 4 AM pattern-recognition prompt inside the active
Execution Market AAS / City-as-a-Service lane. It consumes the source-of-truth
index plus the Bounded Local Count fixture gate and converts memory, IRC/session,
cross-project, and agent-coordination insights into one conservative compounding
map. It records no operator answer, approval, answer receipt, collection,
customer/worker/public surface, dispatch, runtime mutation, reputation, payment,
location/private-context release, authority claim, worker doctrine, or stopped
project integration.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_bounded_local_count_fixture_gate import (
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SCHEMA,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_STATUS,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_BLOCKED_CLAIMS,
    REQUIRED_BLOCKED_CLAIMS,
    load_aas_bounded_local_count_fixture_gate,
)
from .aas_source_of_truth_index import (
    AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
    AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM,
    AAS_SOURCE_OF_TRUTH_INDEX_SCHEMA,
    AAS_SOURCE_OF_TRUTH_INDEX_STATUS,
    SOURCE_OF_TRUTH_BLOCKED_CLAIMS,
    load_aas_source_of_truth_index,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_SCHEMA = (
    "city_ops.aas_bounded_local_count_pattern_compounder.v1"
)
AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_FILENAME = (
    "aas_bounded_local_count_pattern_compounder.json"
)
AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_SAFE_CLAIM = (
    "internal_admin_aas_4am_bounded_local_count_pattern_compounder_2026_06_13_landed"
)
AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_ID = (
    "execution_market.aas.bounded_local_count.pattern_compounder.2026_06_13_0400"
)
AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_STATUS = (
    "internal_admin_pattern_compounder_only_no_answer_no_approval_no_runtime_or_external_promotion"
)

PATTERN_QUESTIONS = [
    "what_patterns_emerge_from_memory_system_data",
    "how_irc_coordination_insights_inform_strategy",
    "what_cross_project_intelligence_flows_create_multiplier_effects",
    "which_agent_coordination_patterns_scale_best",
]

COMPOUNDER_FALSE_FLAGS = {
    "compounder_records_operator_answer": False,
    "compounder_records_operator_approval": False,
    "compounder_selects_answer_value": False,
    "compounder_creates_answer_receipt": False,
    "compounder_authorizes_collection": False,
    "compounder_creates_customer_public_or_worker_surface": False,
    "compounder_creates_catalog_pricing_quote_route_queue_or_dispatch": False,
    "compounder_mutates_runtime_acontext_irc_or_session_manager": False,
    "compounder_writes_or_retrieves_live_acontext": False,
    "compounder_emits_erc8004_reputation_or_worker_skill_dna": False,
    "compounder_reverifies_payment_or_production": False,
    "compounder_exposes_exact_location_raw_metadata_private_context_or_pii": False,
    "compounder_grants_domain_authority_claims": False,
    "compounder_publishes_worker_copyable_doctrine": False,
    "compounder_integrates_or_expands_stopped_projects": False,
}

COMPOUNDER_BLOCKED_CLAIMS = [
    *SOURCE_OF_TRUTH_BLOCKED_CLAIMS,
    *AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_BLOCKED_CLAIMS,
    "bounded_local_count_pattern_compounder_records_operator_answer",
    "bounded_local_count_pattern_compounder_records_operator_approval",
    "bounded_local_count_pattern_compounder_selects_answer_value",
    "bounded_local_count_pattern_compounder_creates_answer_receipt",
    "bounded_local_count_pattern_compounder_authorizes_collection_site_access_or_worker_tasking",
    "bounded_local_count_pattern_compounder_creates_customer_public_or_worker_surface",
    "bounded_local_count_pattern_compounder_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "bounded_local_count_pattern_compounder_mutates_runtime_acontext_irc_or_session_manager",
    "bounded_local_count_pattern_compounder_writes_or_retrieves_live_acontext",
    "bounded_local_count_pattern_compounder_emits_erc8004_reputation_or_worker_skill_dna",
    "bounded_local_count_pattern_compounder_reverifies_payment_or_production",
    "bounded_local_count_pattern_compounder_releases_exact_location_raw_metadata_private_context_or_pii",
    "bounded_local_count_pattern_compounder_grants_domain_legal_safety_repair_insurance_or_sla_authority",
    "bounded_local_count_pattern_compounder_publishes_worker_copyable_doctrine",
    "bounded_local_count_pattern_compounder_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(COMPOUNDER_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_value_selected",
    "answer_receipt_created",
    "collection_authorized",
    "customer_copy_ready",
    "worker_instruction_ready",
    "public_catalog_ready",
    "dispatch_ready",
    "runtime_mutation_ready",
    "live_acontext_ready",
    "irc_session_manager_mutated",
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


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"AAS bounded count compounder claim overlap: {sorted(overlap)}"
        )


def _assert_source_index(source_index: dict[str, Any]) -> None:
    if source_index.get("schema") != AAS_SOURCE_OF_TRUTH_INDEX_SCHEMA:
        raise CityOpsContractError("AAS bounded count compounder source index schema drift")
    if source_index.get("index_status") != AAS_SOURCE_OF_TRUTH_INDEX_STATUS:
        raise CityOpsContractError("AAS bounded count compounder source index status drift")
    safe = set(source_index.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS bounded count compounder source index safe claim missing")
    posture = source_index.get("current_no_answer_posture", {})
    if posture.get("operator_answer_recorded") is not False:
        raise CityOpsContractError("AAS bounded count compounder source index records answer")
    if posture.get("operator_approval_recorded") is not False:
        raise CityOpsContractError("AAS bounded count compounder source index records approval")
    if posture.get("selected_decision") is not None:
        raise CityOpsContractError("AAS bounded count compounder source index selected decision")
    firewall = source_index.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS bounded count compounder source index allowed {key}")


def _assert_fixture_gate(fixture_gate: dict[str, Any]) -> None:
    if fixture_gate.get("schema") != AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SCHEMA:
        raise CityOpsContractError("AAS bounded count compounder fixture gate schema drift")
    if fixture_gate.get("gate_status") != AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_STATUS:
        raise CityOpsContractError("AAS bounded count compounder fixture gate status drift")
    safe = set(fixture_gate.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS bounded count compounder fixture gate safe claim missing")
    state = fixture_gate.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
        "collection_authorized",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS bounded count compounder fixture gate promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS bounded count compounder fixture gate selected decision")
    if state.get("recommended_posture") != "pause_aas_proof_layering":
        raise CityOpsContractError("AAS bounded count compounder fixture gate posture drift")
    required = fixture_gate.get("fixture_schema", {}).get("required_blocked_claims", [])
    if set(REQUIRED_BLOCKED_CLAIMS) - set(required):
        raise CityOpsContractError("AAS bounded count compounder fixture gate blockers drift")


def _pattern_compounder_rows() -> list[dict[str, str]]:
    return [
        {
            "question": "what_patterns_emerge_from_memory_system_data",
            "pattern": "memory_compounds_when_it_stores_reviewed_count_fields_not_raw_context",
            "aas_multiplier": "future AAS sessions inherit answer_value count_question observation_window uncertainty coverage_limits redaction_state blocked_claims and fixture_digest without rereading private or stale material",
            "first_safe_use_after_answer_receipt": "reviewed_summary_memory_row_for_one_bounded_count_packet",
            "blocked_promotion": "live_acontext_write_retrieve_raw_transcript_replay_private_context_or_exact_location_release",
        },
        {
            "question": "how_irc_coordination_insights_inform_strategy",
            "pattern": "irc_coordination_scales_through_invariant_handoff_capsules",
            "aas_multiplier": "agents coordinate by source_file source_digest safe_claim blocked_claims next_gate and posture instead of raw chat replay or implicit permission",
            "first_safe_use_after_answer_receipt": "handoff_capsule_fields_only_no_runtime_session_manager_mutation",
            "blocked_promotion": "irc_runtime_mutation_autorouting_message_replay_worker_instruction_or_session_secret_exposure",
        },
        {
            "question": "what_cross_project_intelligence_flows_create_multiplier_effects",
            "pattern": "cross_project_intelligence_is_a_stop_filter_before_it_is_a_router",
            "aas_multiplier": "stale or attractive adjacent work becomes an explicit skip reason while the selected Bounded Local Count lane stays narrow",
            "first_safe_use_after_answer_receipt": "decision_filter_row_that_allows_only_the_selected_bounded_count_value",
            "blocked_promotion": "autojob_frontier_academy_kk_v2_karmacadabra_customer_catalog_dispatch_payment_or_reputation_movement",
        },
        {
            "question": "which_agent_coordination_patterns_scale_best",
            "pattern": "one_verified_next_gate_scales_better_than_more_agents_or_more_wrappers",
            "aas_multiplier": "agent quality is measured by boundary survival uncertainty adjacency coverage-limit visibility redaction preservation and refusing blocked claims",
            "first_safe_use_after_answer_receipt": "internal_admin_boundary_preservation_scorecard_only",
            "blocked_promotion": "public_dashboard_worker_visible_score_erc8004_reputation_worker_skill_dna_or_payment_production_claim",
        },
    ]


def _compounding_sequence() -> list[dict[str, str]]:
    return [
        {
            "step": "priority_firewall",
            "input": "DREAM-PRIORITIES.md",
            "output": "stopped_projects_refused_before_any_work",
        },
        {
            "step": "answer_menu",
            "input": "2 AM Bounded Local Count operator selection brief",
            "output": "exactly_one_future_answer_value_menu_no_answer_recorded",
        },
        {
            "step": "fixture_gate",
            "input": AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME,
            "output": "bounded_question_window_method_uncertainty_coverage_redaction_blockers_enforced",
        },
        {
            "step": "integration_map",
            "input": "3 AM Bounded Local Count system integration map",
            "output": "memory_irc_decision_filter_observability_seams_named_but_inert",
        },
        {
            "step": "pattern_compounder",
            "input": AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
            "output": "one_next_gate_after_real_answer_receipt_no_runtime_or_external_promotion",
        },
    ]


def build_aas_bounded_local_count_pattern_compounder(
    *,
    artifact_dir: str | Path | None = None,
    source_index: dict[str, Any] | None = None,
    fixture_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic 4 AM Bounded Local Count pattern compounder."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    index = source_index or load_aas_source_of_truth_index(artifact_dir=source_dir)
    gate = fixture_gate or load_aas_bounded_local_count_fixture_gate(artifact_dir=source_dir)
    _assert_source_index(index)
    _assert_fixture_gate(gate)

    safe_to_claim = _dedupe(
        [
            *index["claim_boundaries"]["safe_to_claim"],
            *gate["claim_boundaries"]["safe_to_claim"],
            AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *index["claim_boundaries"]["do_not_claim_yet"],
            *gate["claim_boundaries"]["do_not_claim_yet"],
            *COMPOUNDER_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    packet: dict[str, Any] = {
        "schema": AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_SCHEMA,
        "compounder_id": AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_ID,
        "compounder_status": AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_STATUS,
        "source_index": {
            "file": AAS_SOURCE_OF_TRUTH_INDEX_FILENAME,
            "schema": index["schema"],
            "safe_claim": AAS_SOURCE_OF_TRUTH_INDEX_SAFE_CLAIM,
            "digest_sha256": _stable_digest(index),
        },
        "source_fixture_gate": {
            "file": AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME,
            "schema": gate["schema"],
            "safe_claim": AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM,
            "digest_sha256": _stable_digest(gate),
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service internal/admin planning",
            "source_precedence": "dream_priorities_wins_over_stale_cron_payload",
            "active_posture": "pause_aas_proof_layering",
        },
        "pattern_questions": list(PATTERN_QUESTIONS),
        "pattern_compounder_rows": _pattern_compounder_rows(),
        "compounding_sequence": _compounding_sequence(),
        "future_after_one_real_answer_only": {
            "first_gate": "create_one_separate_digest_backed_bounded_local_count_answer_receipt",
            "second_gate": "validate_exactly_one_packet_against_aas_bounded_local_count_fixture_gate",
            "third_gate": "only_then_create_reviewed_summary_integration_packet_disabled_by_default",
            "still_not_authorized": [
                "collection",
                "customer_public_worker_surface",
                "catalog_pricing_quote_route_queue_or_dispatch",
                "runtime_acontext_irc_session_manager_mutation",
                "erc8004_reputation_or_worker_skill_dna",
                "payment_or_production_change",
                "exact_location_raw_metadata_private_context_or_pii_release",
                "domain_authority_or_worker_copyable_doctrine",
                "stopped_project_integration",
            ],
        },
        "readiness": {
            "internal_admin_pattern_compounder_landed": True,
            "source_index_verified": True,
            "bounded_local_count_fixture_gate_verified": True,
            "pattern_questions_answered_inside_aas_only": True,
            "default_off_non_authorizing": True,
            **COMPOUNDER_FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "stopped_project_firewall": {
            "source": "DREAM-PRIORITIES.md explicit stop list",
            "autojob_work_allowed": False,
            "frontier_academy_work_allowed": False,
            "kk_v2_work_allowed": False,
            "karmacadabra_v2_work_allowed": False,
        },
        "operator_guidance": {
            "if_no_real_answer": "hold_pause_aas_proof_layering_do_not_add_more_no_answer_wrappers",
            "if_real_answer_exists": "create_one_separate_digest_backed_bounded_local_count_answer_receipt_first",
            "recommended_first_answer_value": "bounded_local_count.visible_posted_state_count.v1",
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "not_runtime_or_dashboard_spec": True,
        },
        "compounder_digest_sha256": "",
    }
    packet["compounder_digest_sha256"] = _stable_digest(
        {k: v for k, v in packet.items() if k != "compounder_digest_sha256"}
    )
    _assert_pattern_compounder(packet, source_index=index, fixture_gate=gate)
    return packet


def _assert_pattern_compounder(
    packet: dict[str, Any], *, source_index: dict[str, Any], fixture_gate: dict[str, Any]
) -> None:
    _assert_source_index(source_index)
    _assert_fixture_gate(fixture_gate)
    if packet.get("schema") != AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_SCHEMA:
        raise CityOpsContractError("AAS bounded count compounder schema drift")
    if packet.get("compounder_id") != AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_ID:
        raise CityOpsContractError("AAS bounded count compounder id drift")
    if packet.get("compounder_status") != AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_STATUS:
        raise CityOpsContractError("AAS bounded count compounder status drift")
    if packet.get("source_index", {}).get("digest_sha256") != _stable_digest(source_index):
        raise CityOpsContractError("AAS bounded count compounder source index digest drift")
    if packet.get("source_fixture_gate", {}).get("digest_sha256") != _stable_digest(fixture_gate):
        raise CityOpsContractError("AAS bounded count compounder fixture gate digest drift")

    priority = packet.get("governing_priority", {})
    if priority.get("active_posture") != "pause_aas_proof_layering":
        raise CityOpsContractError("AAS bounded count compounder promoted posture")
    if priority.get("allowed_lane") != "Execution Market AAS / City-as-a-Service internal/admin planning":
        raise CityOpsContractError("AAS bounded count compounder allowed lane drift")

    if packet.get("pattern_questions") != PATTERN_QUESTIONS:
        raise CityOpsContractError("AAS bounded count compounder question drift")
    rows = packet.get("pattern_compounder_rows", [])
    if [row.get("question") for row in rows] != PATTERN_QUESTIONS:
        raise CityOpsContractError("AAS bounded count compounder rows drift")
    for row in rows:
        if "blocked_promotion" not in row or not row["blocked_promotion"]:
            raise CityOpsContractError("AAS bounded count compounder row missing blocker")

    if [row.get("step") for row in packet.get("compounding_sequence", [])] != [
        "priority_firewall",
        "answer_menu",
        "fixture_gate",
        "integration_map",
        "pattern_compounder",
    ]:
        raise CityOpsContractError("AAS bounded count compounder sequence drift")

    future = packet.get("future_after_one_real_answer_only", {})
    if future.get("first_gate") != "create_one_separate_digest_backed_bounded_local_count_answer_receipt":
        raise CityOpsContractError("AAS bounded count compounder first future gate drift")
    if "runtime_acontext_irc_session_manager_mutation" not in future.get("still_not_authorized", []):
        raise CityOpsContractError("AAS bounded count compounder runtime block missing")

    readiness = packet.get("readiness", {})
    for key, expected in COMPOUNDER_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS bounded count compounder promoted readiness {key}")

    safe = set(packet.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(packet.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS bounded count compounder safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS bounded count compounder forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(COMPOUNDER_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS bounded count compounder missing blocked claims: {sorted(missing_blocked)}"
        )
    _assert_no_claim_overlap(list(safe), list(blocked))

    firewall = packet.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS bounded count compounder allowed {key}")

    guidance = packet.get("operator_guidance", {})
    if guidance.get("if_no_real_answer") != "hold_pause_aas_proof_layering_do_not_add_more_no_answer_wrappers":
        raise CityOpsContractError("AAS bounded count compounder no-answer guidance drift")
    if guidance.get("not_customer_copy") is not True:
        raise CityOpsContractError("AAS bounded count compounder guidance promoted customer copy")

    expected_digest = _stable_digest(
        {k: v for k, v in packet.items() if k != "compounder_digest_sha256"}
    )
    if packet.get("compounder_digest_sha256") != expected_digest:
        raise CityOpsContractError("AAS bounded count compounder digest drift")


def write_aas_bounded_local_count_pattern_compounder(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    packet = build_aas_bounded_local_count_pattern_compounder(artifact_dir=target_dir)
    target_path = target_dir / AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_FILENAME
    target_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path


def load_aas_bounded_local_count_pattern_compounder(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_BOUNDED_LOCAL_COUNT_PATTERN_COMPOUNDER_FILENAME
    packet = json.loads(path.read_text(encoding="utf-8"))
    source_index = load_aas_source_of_truth_index(artifact_dir=source_dir)
    fixture_gate = load_aas_bounded_local_count_fixture_gate(artifact_dir=source_dir)
    _assert_pattern_compounder(packet, source_index=source_index, fixture_gate=fixture_gate)
    return packet
