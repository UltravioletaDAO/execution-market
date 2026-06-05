"""Internal/admin 4 AM pattern-recognition multiplier ladder for AAS.

This artifact answers the dream-session pattern question without crossing the
current AAS boundary. It connects the current operator answer receipt gate with
the older reviewed intelligence-flow compounder and turns both into a small
read-only ladder: what patterns compound, which coordination habits scale, and
which gates must stay closed until a separate explicit operator answer exists.

It records no operator answer or approval, performs no live Acontext work,
mutates no IRC/session manager, creates no public/customer/worker surface,
enables no queue or dispatch, emits no reputation/Worker Skill DNA, reverifies
no payment/production state, exposes no GPS/raw metadata/private context, and
uses no stopped project as an active source.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_intelligence_flow_compounder import (
    AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME,
    AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM,
    AAS_INTELLIGENCE_FLOW_COMPOUNDER_SCHEMA,
    INTELLIGENCE_FLOW_BLOCKED_CLAIMS,
    load_aas_intelligence_flow_compounder,
)
from .aas_operator_answer_receipt_gate import (
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME,
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM,
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_SCHEMA,
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_STATUS,
    RECEIPT_GATE_BLOCKED_CLAIMS,
    RECEIPT_GATE_FALSE_FLAGS,
    load_aas_operator_answer_receipt_gate,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SCHEMA = (
    "city_ops.aas_four_am_pattern_recognition_multiplier_ladder.v1"
)
AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME = (
    "aas_four_am_pattern_recognition_multiplier_ladder.json"
)
AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SAFE_CLAIM = (
    "internal_admin_aas_4am_pattern_recognition_multiplier_ladder_landed"
)
AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_ID = (
    "execution_market.aas.pattern_recognition_multiplier_ladder.2026_06_05_0400"
)
AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_STATUS = (
    "read_only_pattern_recognition_no_answer_no_runtime_or_external_promotion"
)

LADDER_FALSE_FLAGS = {
    **RECEIPT_GATE_FALSE_FLAGS,
    "pattern_ladder_records_operator_answer": False,
    "pattern_ladder_records_operator_approval": False,
    "pattern_ladder_selects_future_answer": False,
    "pattern_ladder_creates_answer_receipt": False,
    "pattern_ladder_approves_product_exposure": False,
    "pattern_ladder_approves_runtime_memory": False,
    "pattern_ladder_repairs_docker": False,
    "pattern_ladder_writes_live_acontext": False,
    "pattern_ladder_retrieves_live_acontext": False,
    "pattern_ladder_mutates_irc_session_manager": False,
    "pattern_ladder_enables_cross_project_autorouting": False,
    "pattern_ladder_creates_customer_copy": False,
    "pattern_ladder_creates_worker_instruction": False,
    "pattern_ladder_launches_queue_or_dispatch": False,
    "pattern_ladder_emits_reputation_or_worker_skill_dna": False,
    "pattern_ladder_reverifies_payment_or_production": False,
    "pattern_ladder_exposes_gps_or_raw_metadata": False,
    "pattern_ladder_releases_private_context": False,
    "pattern_ladder_grants_authority_claims": False,
    "pattern_ladder_publishes_worker_doctrine": False,
    "pattern_ladder_uses_stopped_projects_as_active_sources": False,
}

PATTERN_RECOGNITION_BLOCKED_CLAIMS = [
    *RECEIPT_GATE_BLOCKED_CLAIMS,
    *INTELLIGENCE_FLOW_BLOCKED_CLAIMS,
    "pattern_recognition_ladder_records_operator_answer",
    "pattern_recognition_ladder_records_operator_approval",
    "pattern_recognition_ladder_selects_future_answer",
    "pattern_recognition_ladder_creates_answer_receipt",
    "pattern_recognition_ladder_treats_patterns_as_approval",
    "pattern_recognition_ladder_repairs_docker_or_starts_acontext",
    "pattern_recognition_ladder_writes_or_retrieves_live_acontext",
    "pattern_recognition_ladder_mutates_irc_session_manager",
    "pattern_recognition_ladder_enables_cross_project_autorouting",
    "pattern_recognition_ladder_creates_public_customer_worker_surface",
    "pattern_recognition_ladder_authorizes_catalog_pricing_queue_or_dispatch",
    "pattern_recognition_ladder_emits_erc8004_reputation_or_worker_skill_dna",
    "pattern_recognition_ladder_reverifies_payment_or_production",
    "pattern_recognition_ladder_releases_exact_gps_or_raw_metadata",
    "pattern_recognition_ladder_releases_private_context",
    "pattern_recognition_ladder_grants_domain_authority_claims",
    "pattern_recognition_ladder_publishes_worker_copyable_doctrine",
    "pattern_recognition_ladder_integrates_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(PATTERN_RECOGNITION_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_record_created",
    "product_exposure_approved",
    "runtime_memory_wiring_approved",
    "docker_repaired",
    "live_acontext_ready",
    "runtime_parity_proven",
    "irc_session_manager_mutated",
    "cross_project_autorouting_ready",
    "customer_copy_ready",
    "public_dashboard_ready",
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


def build_aas_four_am_pattern_recognition_multiplier_ladder(
    *,
    artifact_dir: str | Path | None = None,
    proof_artifact_dir: str | Path | None = None,
    answer_gate: dict[str, Any] | None = None,
    compounder: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic 4 AM pattern-recognition ladder."""

    package_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    proof_dir = Path(proof_artifact_dir) if proof_artifact_dir else _default_proof_block_dir()
    gate = answer_gate or load_aas_operator_answer_receipt_gate(artifact_dir=package_dir)
    source_compounder = compounder or load_aas_intelligence_flow_compounder(
        artifact_dir=proof_dir
    )
    _assert_answer_gate_conservative(gate)
    _assert_compounder_conservative(source_compounder)

    safe_to_claim = _dedupe(
        [
            *gate["claim_boundaries"]["safe_to_claim"],
            *source_compounder["claim_boundaries"]["safe_to_claim"],
            AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM,
            AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM,
            AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *gate["claim_boundaries"]["do_not_claim_yet"],
            *source_compounder["claim_boundaries"]["do_not_claim_yet"],
            *PATTERN_RECOGNITION_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    ladder = {
        "schema": AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SCHEMA,
        "ladder_id": AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_ID,
        "ladder_status": AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_STATUS,
        "source_operator_answer_gate": _source_ref(
            AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME,
            AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM,
            gate,
            source_role="current_future_answer_contract",
        ),
        "source_intelligence_flow_compounder": _source_ref(
            AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME,
            AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM,
            source_compounder,
            source_role="reviewed_cross_project_intelligence_filter",
        ),
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME,
                AAS_INTELLIGENCE_FLOW_COMPOUNDER_FILENAME,
            ],
            "forbidden_inputs": [
                "raw_transcripts",
                "unreviewed_memory",
                "private_operator_context",
                "live_acontext_sink_writes",
                "live_acontext_retrievals",
                "payment_processor_probe",
                "production_health_probe",
                "gps_or_raw_metadata_payloads",
                "customer_copy_drafts",
                "worker_instruction_templates",
                "stopped_project_codebases_as_active_sources",
            ],
        },
        "access_policy": _access_policy(),
        "readiness": _readiness(),
        "pattern_recognition_cards": _pattern_recognition_cards(),
        "multiplier_edges": _multiplier_edges(),
        "scaling_rules": _scaling_rules(),
        "next_required_gates": _next_required_gates(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "ladder_verdict": "pattern_recognition_multiplier_ladder_landed_internal_only",
        "operator_instruction": (
            "Use this as the 4 AM pattern handoff: extract useful coordination "
            "connections, then stop at the operator answer receipt gate. Patterns "
            "are not approval. Do not mutate runtime memory, IRC/session managers, "
            "customer/public/worker surfaces, queue/dispatch, payment/reputation, "
            "GPS/raw metadata, private context, worker doctrine, or stopped projects."
        ),
    }
    _assert_ladder_conservative(ladder)
    return ladder


def write_aas_four_am_pattern_recognition_multiplier_ladder(
    *,
    artifact_dir: str | Path | None = None,
    proof_artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic 4 AM pattern-recognition ladder."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    ladder = build_aas_four_am_pattern_recognition_multiplier_ladder(
        artifact_dir=base_dir,
        proof_artifact_dir=proof_artifact_dir,
    )
    path = base_dir / AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME
    path.write_text(json.dumps(ladder, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_four_am_pattern_recognition_multiplier_ladder(
    *,
    artifact_dir: str | Path | None = None,
    proof_artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load and validate the persisted 4 AM pattern-recognition ladder."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    with (base_dir / AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        ladder = json.load(fh)
    expected = build_aas_four_am_pattern_recognition_multiplier_ladder(
        artifact_dir=base_dir,
        proof_artifact_dir=proof_artifact_dir,
    )
    _assert_ladder_conservative(ladder)
    if ladder != expected:
        raise CityOpsContractError("4 AM pattern-recognition multiplier ladder drifted")
    return ladder


def _source_ref(
    filename: str,
    safe_claim: str,
    payload: dict[str, Any],
    *,
    source_role: str,
) -> dict[str, Any]:
    return {
        "file": filename,
        "source_role": source_role,
        "safe_claim": safe_claim,
        "digest_sha256": _stable_digest(payload),
    }


def _access_policy() -> dict[str, bool | str]:
    access: dict[str, bool | str] = {
        "audience": "internal_admin_only",
        "requires_admin_context": True,
    }
    for key in [
        "network_route_registered",
        "public_route_registered",
        "customer_visible",
        "worker_visible",
        "operator_queue_launched",
        "dispatch_enabled",
        "runtime_adapter_registered",
        "runtime_adapter_enabled",
        "irc_session_manager_mutated",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "emits_reputation_receipts",
        "exposes_gps_or_metadata",
        "publishes_worker_doctrine",
    ]:
        access[key] = False
    return access


def _readiness() -> dict[str, bool]:
    readiness = {
        "pattern_ladder_landed": True,
        "source_answer_gate_consumed": True,
        "source_intelligence_compounder_consumed": True,
        "memory_patterns_mapped_as_planning_only": True,
        "irc_coordination_mapped_as_handoff_shape_only": True,
        "cross_project_intelligence_mapped_as_firewall_only": True,
        "scalable_coordination_rules_documented": True,
        "next_operator_gate_preserved": True,
    }
    readiness.update(LADDER_FALSE_FLAGS)
    return readiness


def _pattern_recognition_cards() -> list[dict[str, str]]:
    return [
        {
            "pattern": "memory_system_data",
            "insight": "Memory compounds when each handoff carries source ref, digest, safe claim, blocked claims, and next gate instead of raw context replay.",
            "safe_use": "planning and boundary preservation only",
            "blocked_until": "explicit runtime-memory operator answer plus Docker/Acontext prerequisite proof",
        },
        {
            "pattern": "irc_coordination",
            "insight": "IRC/session insights scale as packet discipline: four IDs, no raw transcript ingestion, no private context, and fail-closed routing when answer state is missing.",
            "safe_use": "handoff format and future adapter contract language only",
            "blocked_until": "separate session adapter contract plus explicit operator answer before runtime mutation",
        },
        {
            "pattern": "cross_project_intelligence_flows",
            "insight": "The highest-value cross-project flow tonight is negative routing: stopped projects provide firewall signals, not active implementation sources.",
            "safe_use": "decision-support prioritization inside Execution Market AAS only",
            "blocked_until": "one explicit validated operator receipt before product/runtime fork movement",
        },
        {
            "pattern": "agent_coordination_scaling",
            "insight": "The coordination pattern that scales best is one-next-proof discipline; every agent should improve a gate or stop, not invent approval from momentum.",
            "safe_use": "internal/admin agent success scoring",
            "blocked_until": "separate internal metric gate with no public/customer/worker visibility",
        },
    ]


def _multiplier_edges() -> list[dict[str, str]]:
    return [
        {
            "from": "operator_answer_receipt_gate",
            "to": "pattern_ladder",
            "multiplier": "future explicit answers can be checked against a stable contract instead of interpreted from prose",
            "boundary": "does not create that answer",
        },
        {
            "from": "intelligence_flow_compounder",
            "to": "pattern_ladder",
            "multiplier": "cross-project insights become quarantine and prioritization rules rather than autorouting",
            "boundary": "does not activate stopped projects or customer surfaces",
        },
        {
            "from": "memory_and_irc_handoff_shape",
            "to": "future_agent_runs",
            "multiplier": "agents can resume with invariant IDs and blocked-claim context without exposing raw transcripts or private state",
            "boundary": "does not write live Acontext or mutate session managers",
        },
    ]


def _scaling_rules() -> list[dict[str, str]]:
    return [
        {
            "rule": "carry_four_fields_first",
            "description": "Every handoff must name source ref, safe claim, do-not-claim-yet set, and next required gate before any brainstorm.",
        },
        {
            "rule": "negative_routing_is_value",
            "description": "When DREAM-PRIORITIES stops a project, preserving that stop is a successful intelligence flow, not a missed task.",
        },
        {
            "rule": "patterns_are_not_permissions",
            "description": "A compelling cross-project connection can become a planning card only; movement still requires the answer receipt gate.",
        },
        {
            "rule": "truth_beats_momentum",
            "description": "If no new truth is available, choose pause_aas_proof_layering or keep_both_lanes_held instead of adding launch-shaped artifacts.",
        },
    ]


def _next_required_gates() -> list[dict[str, str]]:
    return [
        {
            "if_saúl_gives_no_answer": "pause_aas_proof_layering",
            "gate": "stop_no_movement_pause_proof_layering",
        },
        {
            "if_saúl_wants_product_lane": "create_retail_reality_answer_or_hold_record",
            "gate": "create_retail_reality_answer_or_hold_record_before_any_public_or_dispatch_step",
        },
        {
            "if_saúl_wants_runtime_memory_lane": "create_runtime_memory_operator_answer_record",
            "gate": "create_runtime_memory_operator_answer_record_then_restore_docker_and_rerun_read_only_inventory",
        },
        {
            "if_saúl_wants_hold": "keep_both_lanes_held",
            "gate": "stop_no_movement_keep_both_lanes_held",
        },
    ]


def _assert_answer_gate_conservative(gate: dict[str, Any]) -> None:
    if gate.get("schema") != AAS_OPERATOR_ANSWER_RECEIPT_GATE_SCHEMA:
        raise CityOpsContractError("4 AM pattern ladder answer gate schema drift")
    if gate.get("gate_status") != AAS_OPERATOR_ANSWER_RECEIPT_GATE_STATUS:
        raise CityOpsContractError("4 AM pattern ladder answer gate status drift")
    safe = set(gate.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("4 AM pattern ladder answer gate safe claim missing")
    _assert_no_forbidden_safe(safe, "answer gate")
    blocked = set(gate.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(RECEIPT_GATE_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"4 AM pattern ladder answer gate missing blocked claims: {sorted(missing)}"
        )
    for key, expected in RECEIPT_GATE_FALSE_FLAGS.items():
        if gate.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"4 AM pattern ladder answer gate promoted {key}")


def _assert_compounder_conservative(compounder: dict[str, Any]) -> None:
    if compounder.get("schema") != AAS_INTELLIGENCE_FLOW_COMPOUNDER_SCHEMA:
        raise CityOpsContractError("4 AM pattern ladder compounder schema drift")
    safe = set(compounder.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_INTELLIGENCE_FLOW_COMPOUNDER_SAFE_CLAIM not in safe:
        raise CityOpsContractError("4 AM pattern ladder compounder safe claim missing")
    _assert_no_forbidden_safe(safe, "compounder")
    blocked = set(compounder.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(INTELLIGENCE_FLOW_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"4 AM pattern ladder compounder missing blocked claims: {sorted(missing)}"
        )
    for section in ["derived_from", "access_policy"]:
        values = compounder.get(section, {})
        for key in [
            "writes_live_acontext",
            "retrieves_live_acontext",
            "emits_reputation_receipts",
            "exposes_gps_or_metadata",
            "publishes_worker_doctrine",
        ]:
            if values.get(key) is not False:
                raise CityOpsContractError(f"4 AM pattern ladder compounder promoted {key}")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    _assert_no_forbidden_safe(safe, "ladder")
    missing = set(PATTERN_RECOGNITION_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"4 AM pattern ladder missing blocked claims: {sorted(missing)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"4 AM pattern ladder safe/blocked overlap: {sorted(overlap)}"
        )


def _assert_no_forbidden_safe(safe: set[str], source: str) -> None:
    forbidden = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden:
        raise CityOpsContractError(
            f"4 AM pattern ladder {source} forbidden safe claims: {sorted(forbidden)}"
        )


def _assert_ladder_conservative(ladder: dict[str, Any]) -> None:
    if ladder.get("schema") != AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_SCHEMA:
        raise CityOpsContractError("4 AM pattern ladder schema drift")
    if ladder.get("ladder_status") != AAS_FOUR_AM_PATTERN_RECOGNITION_MULTIPLIER_LADDER_STATUS:
        raise CityOpsContractError("4 AM pattern ladder status drift")
    readiness = ladder.get("readiness", {})
    for key, expected in LADDER_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"4 AM pattern ladder promoted {key}")
    access = ladder.get("access_policy", {})
    for key, value in access.items():
        if key in {"audience", "requires_admin_context"}:
            continue
        if value is not False:
            raise CityOpsContractError(f"4 AM pattern ladder access promoted {key}")
    derived = ladder.get("derived_from", {})
    if derived.get("read_only") is not True:
        raise CityOpsContractError("4 AM pattern ladder is not read-only")
    forbidden_inputs = set(derived.get("forbidden_inputs", []))
    required_forbidden = {
        "raw_transcripts",
        "unreviewed_memory",
        "private_operator_context",
        "live_acontext_sink_writes",
        "live_acontext_retrievals",
        "stopped_project_codebases_as_active_sources",
    }
    if not required_forbidden <= forbidden_inputs:
        raise CityOpsContractError("4 AM pattern ladder missing forbidden inputs")
    _assert_claim_boundaries(
        ladder.get("claim_boundaries", {}).get("safe_to_claim", []),
        ladder.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
