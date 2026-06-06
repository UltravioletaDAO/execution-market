"""Internal/admin implementation roadmap derived from the AAS concept gap matrix.

This roadmap turns the source-backed concept gap matrix into a conservative
planning sequence. It is deliberately not an answer receipt, not an approval
record, not customer/worker/public copy, and not runtime/product movement. Its
job is to make the next AAS planning surface less scattered while preserving the
current June 5 no-answer boundary.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_concept_gap_matrix import (
    AAS_CONCEPT_GAP_MATRIX_FILENAME,
    AAS_CONCEPT_GAP_MATRIX_SAFE_CLAIM,
    AAS_CONCEPT_GAP_MATRIX_SCHEMA,
    AAS_CONCEPT_GAP_MATRIX_STATUS,
    BLOCKED_CLAIMS as CONCEPT_GAP_BLOCKED_CLAIMS,
    load_aas_concept_gap_matrix,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA = (
    "city_ops.aas_concept_gap_implementation_roadmap.v1"
)
AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME = (
    "aas_concept_gap_implementation_roadmap.json"
)
AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM = (
    "internal_admin_aas_concept_gap_implementation_roadmap_landed"
)
AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_ID = (
    "execution_market.aas.concept_gap_implementation_roadmap.2026_06_05_2300"
)
AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS = (
    "internal_admin_planning_sequence_no_answer_no_approval_no_product_or_runtime_promotion"
)

FALSE_FLAGS = {
    "roadmap_records_operator_answer": False,
    "roadmap_records_operator_approval": False,
    "roadmap_creates_answer_receipt": False,
    "roadmap_selects_future_answer": False,
    "roadmap_approves_product_exposure": False,
    "roadmap_creates_customer_public_or_worker_copy": False,
    "roadmap_creates_public_catalog_pricing_quote_or_route": False,
    "roadmap_launches_queue_dispatch_or_worker_instruction": False,
    "roadmap_emits_reputation_or_worker_skill_dna": False,
    "roadmap_reverifies_payment_or_production": False,
    "roadmap_mutates_runtime_acontext_or_irc": False,
    "roadmap_exposes_exact_gps_raw_metadata_or_private_context": False,
    "roadmap_grants_domain_authority": False,
    "roadmap_publishes_worker_copyable_doctrine": False,
    "roadmap_integrates_or_expands_stopped_projects": False,
}

ROADMAP_BLOCKED_CLAIMS = [
    *CONCEPT_GAP_BLOCKED_CLAIMS,
    "concept_gap_roadmap_records_operator_answer",
    "concept_gap_roadmap_records_operator_approval",
    "concept_gap_roadmap_creates_answer_receipt",
    "concept_gap_roadmap_selects_future_answer",
    "concept_gap_roadmap_treats_sequence_rank_as_approval",
    "concept_gap_roadmap_approves_product_exposure",
    "concept_gap_roadmap_creates_customer_public_or_worker_surface",
    "concept_gap_roadmap_authorizes_catalog_pricing_quote_route_queue_or_dispatch",
    "concept_gap_roadmap_creates_worker_instruction",
    "concept_gap_roadmap_emits_erc8004_reputation_or_worker_skill_dna",
    "concept_gap_roadmap_reverifies_payment_or_production",
    "concept_gap_roadmap_mutates_runtime_acontext_or_irc_session_manager",
    "concept_gap_roadmap_releases_exact_gps_raw_metadata_or_private_context",
    "concept_gap_roadmap_grants_legal_regulator_notarial_custody_emergency_safety_repair_insurance_sla_official_report_or_fault_liability_authority",
    "concept_gap_roadmap_publishes_worker_copyable_doctrine",
    "concept_gap_roadmap_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(ROADMAP_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "product_exposure_approved",
    "customer_copy_ready",
    "public_catalog_ready",
    "pricing_ready",
    "queue_ready",
    "dispatch_ready",
    "worker_instruction_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "runtime_parity_proven",
    "live_acontext_ready",
    "irc_session_manager_mutated",
    "gps_release_ready",
    "private_context_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "karmacadabra_v2_ready",
}

LANE_ACTION_OVERRIDES = {
    "retail_reality": {
        "planning_sequence_rank": 1,
        "roadmap_next_planning_slice": "answer_receipt_prerequisite_checklist_only_if_explicit_operator_answer_arrives",
        "why_this_order": "closest held product family, but the boundary requires a real answer before answer/hold record work",
    },
    "document_handoff": {
        "planning_sequence_rank": 2,
        "roadmap_next_planning_slice": "redaction_and_delivery_path_gap_note_maintenance_only",
        "why_this_order": "handoff value is high, but custody/legal/notarial authority must remain blocked",
    },
    "compliance_desk": {
        "planning_sequence_rank": 3,
        "roadmap_next_planning_slice": "delivery_path_hold_gap_review_without_customer_copy",
        "why_this_order": "visible-notice packaging is safer than authority claims, but publication/delivery remains absent",
    },
    "field_asset_ops": {
        "planning_sequence_rank": 4,
        "roadmap_next_planning_slice": "visible_asset_state_fixture_outline_no_repair_or_sla_language",
        "why_this_order": "underdeveloped concept lane with clear low-authority observation vocabulary",
    },
    "event_readiness": {
        "planning_sequence_rank": 5,
        "roadmap_next_planning_slice": "observed_pre_event_blocker_outline_no_permit_security_or_outcome_claim",
        "why_this_order": "useful city-adjacent lane but time pressure makes authority overclaim easy",
    },
    "incident_verification": {
        "planning_sequence_rank": 6,
        "roadmap_next_planning_slice": "observation_uncertainty_language_maintenance_only",
        "why_this_order": "strong validator exists, but emergency/fault/official-report claims remain high risk",
    },
    "local_data_collection": {
        "planning_sequence_rank": 7,
        "roadmap_next_planning_slice": "measurement_uncertainty_rubric_outline_no_dataset_publication",
        "why_this_order": "safe as method discipline, not as representativeness or dataset publication",
    },
    "property_ops": {
        "planning_sequence_rank": 8,
        "roadmap_next_planning_slice": "blocked_claim_quarantine_vocabulary_only",
        "why_this_order": "legal/access/appraisal/remediation risks keep this behind safer lanes",
    },
    "system_integration_runtime_memory": {
        "planning_sequence_rank": 9,
        "roadmap_next_planning_slice": "read_only_runtime_prerequisite_inventory_only_after_explicit_runtime_memory_answer",
        "why_this_order": "route-regret panel says stop runtime layers until new operator/runtime truth exists",
    },
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


def _assert_source_matrix(matrix: dict[str, Any]) -> None:
    if matrix.get("schema") != AAS_CONCEPT_GAP_MATRIX_SCHEMA:
        raise CityOpsContractError("AAS concept gap roadmap source schema drift")
    if matrix.get("matrix_status") != AAS_CONCEPT_GAP_MATRIX_STATUS:
        raise CityOpsContractError("AAS concept gap roadmap source status drift")
    safe = set(matrix.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_CONCEPT_GAP_MATRIX_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS concept gap roadmap source safe claim missing")
    blocked = set(matrix.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(CONCEPT_GAP_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS concept gap roadmap source missing blocked claims: {sorted(missing)}"
        )
    state = matrix.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS concept gap roadmap source promoted {key}")
    firewall = matrix.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS concept gap roadmap source allowed {key}")


def _roadmap_rows(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in matrix.get("concept_gap_rows", []):
        family = row.get("aas_family")
        override = LANE_ACTION_OVERRIDES.get(family)
        if override is None:
            raise CityOpsContractError(f"AAS concept gap roadmap missing lane override: {family}")
        rows.append(
            {
                "aas_family": family,
                "planning_sequence_rank": override["planning_sequence_rank"],
                "source_backed_current_state": row["source_backed_current_state"],
                "implementation_concept_expansion": row["implementation_concept_expansion"],
                "roadmap_next_planning_slice": override["roadmap_next_planning_slice"],
                "why_this_order": override["why_this_order"],
                "next_allowed_without_human_answer": row["next_allowed_without_human_answer"],
                "required_gate_before_any_delivery_or_runtime_movement": "separate_explicit_operator_answer_receipt_then_specific_gate",
                "still_blocked": True,
            }
        )
    rows.sort(key=lambda item: item["planning_sequence_rank"])
    return rows


def build_aas_concept_gap_implementation_roadmap(
    *,
    artifact_dir: str | Path | None = None,
    source_matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin AAS concept-gap roadmap."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    matrix = source_matrix or load_aas_concept_gap_matrix(artifact_dir=source_dir)
    _assert_source_matrix(matrix)

    safe_to_claim = [
        AAS_CONCEPT_GAP_MATRIX_SAFE_CLAIM,
        AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    ]
    do_not_claim_yet = _dedupe(ROADMAP_BLOCKED_CLAIMS)

    roadmap = {
        "schema": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA,
        "roadmap_id": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_ID,
        "roadmap_status": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS,
        "source_matrix": {
            "file": AAS_CONCEPT_GAP_MATRIX_FILENAME,
            "schema": matrix["schema"],
            "matrix_id": matrix["matrix_id"],
            "safe_claim": AAS_CONCEPT_GAP_MATRIX_SAFE_CLAIM,
            "digest_sha256": _stable_digest(matrix),
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service implementation planning",
            "stopped_project_firewall": {
                "autojob_work_allowed": False,
                "frontier_academy_work_allowed": False,
                "kk_v2_work_allowed": False,
                "karmacadabra_v2_work_allowed": False,
            },
        },
        "current_operator_state": {
            "explicit_operator_answer_available": False,
            "operator_approval_recorded": False,
            "answer_receipt_created": False,
            "selected_decision": None,
            "recommended_no_human_posture": "pause_aas_proof_layering_or_keep_both_lanes_held",
        },
        "readiness": dict(FALSE_FLAGS),
        "roadmap_rows": _roadmap_rows(matrix),
        "sequence_rules": [
            "Use ranks as planning order only, never approval order.",
            "Do not create an answer receipt unless an explicit operator answer exists outside this roadmap.",
            "Do not turn roadmap rows into customer, public, worker, pricing, queue, dispatch, reputation, payment, or runtime surfaces.",
            "Prefer observation vocabulary and blocked-claim quarantine over domain-authority language.",
            "Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.",
        ],
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "roadmap_digest_sha256": "",
    }
    roadmap["roadmap_digest_sha256"] = _stable_digest(
        {k: v for k, v in roadmap.items() if k != "roadmap_digest_sha256"}
    )
    _assert_roadmap_conservative(roadmap, source_matrix=matrix)
    return roadmap


def write_aas_concept_gap_implementation_roadmap(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic AAS concept-gap implementation roadmap."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    roadmap = build_aas_concept_gap_implementation_roadmap(artifact_dir=base_dir)
    path = base_dir / AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME
    path.write_text(json.dumps(roadmap, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_concept_gap_implementation_roadmap(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted roadmap."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    roadmap = json.loads(
        (base_dir / AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_matrix = load_aas_concept_gap_matrix(artifact_dir=base_dir)
    _assert_roadmap_conservative(roadmap, source_matrix=source_matrix)
    return roadmap


def _assert_roadmap_conservative(
    roadmap: dict[str, Any], *, source_matrix: dict[str, Any]
) -> None:
    _assert_source_matrix(source_matrix)
    if roadmap.get("schema") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA:
        raise CityOpsContractError("AAS concept gap roadmap schema drift")
    if roadmap.get("roadmap_id") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_ID:
        raise CityOpsContractError("AAS concept gap roadmap id drift")
    if roadmap.get("roadmap_status") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS:
        raise CityOpsContractError("AAS concept gap roadmap status drift")
    source = roadmap.get("source_matrix", {})
    if source.get("digest_sha256") != _stable_digest(source_matrix):
        raise CityOpsContractError("AAS concept gap roadmap source digest drift")

    state = roadmap.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS concept gap roadmap operator state promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS concept gap roadmap selected future decision")

    for key, expected in FALSE_FLAGS.items():
        if roadmap.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS concept gap roadmap readiness promoted {key}")

    expected_families = {row["aas_family"] for row in source_matrix["concept_gap_rows"]}
    rows = roadmap.get("roadmap_rows", [])
    row_families = {row.get("aas_family") for row in rows}
    if row_families != expected_families:
        raise CityOpsContractError("AAS concept gap roadmap row family drift")
    ranks = [row.get("planning_sequence_rank") for row in rows]
    if ranks != sorted(ranks) or ranks != list(range(1, len(rows) + 1)):
        raise CityOpsContractError("AAS concept gap roadmap rank drift")
    for row in rows:
        if row.get("still_blocked") is not True:
            raise CityOpsContractError("AAS concept gap roadmap row unblocked")
        if row.get("required_gate_before_any_delivery_or_runtime_movement") != (
            "separate_explicit_operator_answer_receipt_then_specific_gate"
        ):
            raise CityOpsContractError("AAS concept gap roadmap delivery gate drift")
        next_allowed = str(row.get("next_allowed_without_human_answer"))
        if next_allowed in {"approved", "customer_ready", "dispatch_ready", "runtime_ready", "public_ready"}:
            raise CityOpsContractError("AAS concept gap roadmap promotes without human answer")

    safe = set(roadmap.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(roadmap.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS concept gap roadmap safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS concept gap roadmap forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(ROADMAP_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS concept gap roadmap missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(f"AAS concept gap roadmap claim overlap: {sorted(overlap)}")

    firewall = roadmap.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS concept gap roadmap allowed {key}")
