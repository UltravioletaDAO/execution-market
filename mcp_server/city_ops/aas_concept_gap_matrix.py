"""Source-backed internal/admin AAS concept gap matrix.

This artifact expands the City-as-a-Service/AAS implementation concept map only
as an internal planning matrix. It deliberately avoids the June 5 anti-pattern:
it is not another no-answer wrapper, not an operator-answer artifact, and not an
approval/customer/product/runtime promotion. It consumes reviewed planning docs
by filename + digest and turns them into a conservative gap matrix for future
human-directed planning.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_CONCEPT_GAP_MATRIX_SCHEMA = "city_ops.aas_concept_gap_matrix.v1"
AAS_CONCEPT_GAP_MATRIX_FILENAME = "aas_concept_gap_matrix.json"
AAS_CONCEPT_GAP_MATRIX_SAFE_CLAIM = "internal_admin_aas_concept_gap_matrix_landed"
AAS_CONCEPT_GAP_MATRIX_ID = "execution_market.aas.concept_gap_matrix.2026_06_05_2200"
AAS_CONCEPT_GAP_MATRIX_STATUS = (
    "internal_admin_source_backed_planning_no_answer_no_approval_no_product_or_runtime_promotion"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PLANNING_DIR = REPO_ROOT / "docs" / "planning"

SOURCE_DOCUMENTS = [
    {
        "file": "EXECUTION_MARKET_AAS_CONCEPT_MAP_2026_05_08.md",
        "role": "baseline_adjacent_aas_taxonomy_and_first_concierge_offers",
    },
    {
        "file": "EXECUTION_MARKET_AAS_NEXT_LOW_AUTHORITY_PACKAGING_PLAN_2026_05_23_10PM.md",
        "role": "ranked_low_authority_packaging_plan_for_adjacent_aas_lanes",
    },
    {
        "file": "CITY_AS_A_SERVICE_AAS_PRODUCT_FORK_NEXT_GATE_SELECTOR_2026_06_01.md",
        "role": "current_product_family_next_gate_selector_and_no_human_pause_rule",
    },
    {
        "file": "CITY_AS_A_SERVICE_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_IMPLEMENTATION.md",
        "role": "stop_marker_for_more_route_layers_without_runtime_or_operator_truth",
    },
    {
        "file": "CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_06_05.md",
        "role": "latest_final_wrap_recommending_pause_aas_proof_layering",
    },
]

CONCEPT_ROWS = [
    {
        "aas_family": "retail_reality",
        "source_backed_current_state": "closest product-family review candidate; selected boundary is internal/admin and still pending",
        "small_safe_internal_admin_gap": "draft a hold-vs-answer checklist only after an explicit operator answer; otherwise keep the existing packet held",
        "implementation_concept_expansion": "stale-hours refresh replay shape with source digest, observed-window limits, and no inventory guarantee",
        "next_allowed_without_human_answer": "none_beyond_matrix_or_source_digest_maintenance",
        "priority_if_human_answer_arrives": 1,
    },
    {
        "aas_family": "local_data_collection",
        "source_backed_current_state": "useful held family; needs selected-boundary request before any approval record",
        "small_safe_internal_admin_gap": "plan a one-location measurement uncertainty rubric that keeps representativeness blocked",
        "implementation_concept_expansion": "measurement packet fields for count/method/source-type/uncertainty without dataset publication",
        "next_allowed_without_human_answer": "planning_only_no_fixture_promotion",
        "priority_if_human_answer_arrives": 5,
    },
    {
        "aas_family": "field_asset_ops",
        "source_backed_current_state": "concept-map lane with no active package rung in the current no-answer stack",
        "small_safe_internal_admin_gap": "define a future fixture-spec outline for visible asset state vs obstruction, not repair diagnosis",
        "implementation_concept_expansion": "observed-state checklist separating visibility/functionality/obstruction from warranty/SLA/safety claims",
        "next_allowed_without_human_answer": "concept_outline_only",
        "priority_if_human_answer_arrives": 3,
    },
    {
        "aas_family": "event_readiness",
        "source_backed_current_state": "concept-map lane; time pressure creates safety/permit/vendor-overclaim risk",
        "small_safe_internal_admin_gap": "keep a future venue-readiness fixture outline limited to observed checklist blockers",
        "implementation_concept_expansion": "pre-event snapshot schema separating observed setup state from permit/security/outcome authority",
        "next_allowed_without_human_answer": "concept_outline_only",
        "priority_if_human_answer_arrives": 4,
    },
    {
        "aas_family": "property_ops",
        "source_backed_current_state": "concept-map lane intentionally lower priority because legal/appraisal/access risks are high",
        "small_safe_internal_admin_gap": "only maintain a blocked-claim quarantine map until safer lanes have more proof",
        "implementation_concept_expansion": "single-site visible-condition vocabulary that excludes appraisal/code/legal/insurance/remediation claims",
        "next_allowed_without_human_answer": "blocked_claim_quarantine_only",
        "priority_if_human_answer_arrives": 6,
    },
    {
        "aas_family": "document_handoff",
        "source_backed_current_state": "pending approval-request/read-surface family; no human approval record exists",
        "small_safe_internal_admin_gap": "maintain redaction and delivery-path gap notes; do not create approval record without an explicit answer",
        "implementation_concept_expansion": "handoff proof packet discipline around custody limits, redaction gates, and no legal/notarial authority",
        "next_allowed_without_human_answer": "maintenance_only_no_new_approval_artifact",
        "priority_if_human_answer_arrives": 2,
    },
    {
        "aas_family": "compliance_desk",
        "source_backed_current_state": "one internal label has prior approval posture, but delivery path remains absent",
        "small_safe_internal_admin_gap": "preserve delivery-path hold gap; no customer copy/publication route without separate human authorization",
        "implementation_concept_expansion": "visible-notice compliance snapshot packaging with regulator/legal acceptance explicitly blocked",
        "next_allowed_without_human_answer": "maintenance_only_no_delivery_path",
        "priority_if_human_answer_arrives": 2,
    },
    {
        "aas_family": "incident_verification",
        "source_backed_current_state": "strong validator exists for a future human record; incident-authority risk remains high",
        "small_safe_internal_admin_gap": "keep validator and authority exclusions intact; no approval, report, repair, insurance, or fault claim",
        "implementation_concept_expansion": "incident state snapshot language split into observation, uncertainty, and non-authority disclaimers",
        "next_allowed_without_human_answer": "maintenance_only_no_approval_record",
        "priority_if_human_answer_arrives": 4,
    },
    {
        "aas_family": "system_integration_runtime_memory",
        "source_backed_current_state": "support/control lane; route regret panel says stop adding route layers without new truth",
        "small_safe_internal_admin_gap": "use as a prerequisite checklist only; no Docker/Acontext/runtime/IRC mutation in this matrix",
        "implementation_concept_expansion": "future answer-receipt-driven runtime checklist: read-only inventory before any live write/retrieve parity attempt",
        "next_allowed_without_human_answer": "pause_aas_proof_layering",
        "priority_if_human_answer_arrives": 7,
    },
]

FALSE_FLAGS = {
    "matrix_records_operator_answer": False,
    "matrix_records_operator_approval": False,
    "matrix_creates_answer_receipt": False,
    "matrix_selects_future_answer": False,
    "matrix_approves_product_exposure": False,
    "matrix_creates_customer_copy": False,
    "matrix_creates_public_catalog_or_route": False,
    "matrix_sets_pricing_or_customer_quote": False,
    "matrix_launches_queue_or_dispatch": False,
    "matrix_creates_worker_instruction": False,
    "matrix_emits_reputation_or_worker_skill_dna": False,
    "matrix_reverifies_payment_or_production": False,
    "matrix_mutates_runtime_or_acontext": False,
    "matrix_mutates_irc_session_manager": False,
    "matrix_exposes_exact_gps_or_raw_metadata": False,
    "matrix_releases_private_context": False,
    "matrix_grants_domain_authority": False,
    "matrix_publishes_worker_copyable_doctrine": False,
    "matrix_uses_stopped_projects_as_sources": False,
}

BLOCKED_CLAIMS = [
    "concept_gap_matrix_records_operator_answer",
    "concept_gap_matrix_records_operator_approval",
    "concept_gap_matrix_creates_answer_receipt",
    "concept_gap_matrix_selects_future_answer",
    "concept_gap_matrix_treats_gap_rank_as_approval",
    "concept_gap_matrix_approves_product_exposure",
    "concept_gap_matrix_creates_customer_public_or_worker_surface",
    "concept_gap_matrix_authorizes_catalog_pricing_quote_queue_or_dispatch",
    "concept_gap_matrix_emits_erc8004_reputation_or_worker_skill_dna",
    "concept_gap_matrix_reverifies_payment_or_production",
    "concept_gap_matrix_mutates_runtime_acontext_or_irc_session_manager",
    "concept_gap_matrix_releases_exact_gps_raw_metadata_or_private_context",
    "concept_gap_matrix_grants_legal_regulator_notarial_custody_emergency_safety_repair_insurance_sla_official_report_or_fault_liability_authority",
    "concept_gap_matrix_publishes_worker_copyable_doctrine",
    "concept_gap_matrix_integrates_or_expands_stopped_projects",
    "retail_reality_customer_exposure_approved_by_matrix",
    "local_data_collection_dataset_or_representativeness_claim_approved_by_matrix",
    "field_asset_ops_repair_diagnosis_or_sla_claim_approved_by_matrix",
    "event_readiness_safety_permit_security_vendor_or_outcome_claim_approved_by_matrix",
    "property_ops_appraisal_code_legal_access_insurance_or_remediation_claim_approved_by_matrix",
    "document_handoff_legal_notarial_custody_or_acceptance_claim_approved_by_matrix",
    "compliance_desk_regulator_legal_sufficiency_or_publication_claim_approved_by_matrix",
    "incident_verification_emergency_official_report_fault_liability_or_repair_claim_approved_by_matrix",
    "system_integration_runtime_memory_write_retrieve_or_parity_claim_approved_by_matrix",
]

FORBIDDEN_SAFE_CLAIMS = set(BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "product_exposure_approved",
    "customer_copy_ready",
    "catalog_ready",
    "pricing_ready",
    "dispatch_ready",
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


def _stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_digest(path: Path) -> str:
    if not path.exists():
        raise CityOpsContractError(f"AAS concept gap matrix source missing: {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _source_documents() -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for source in SOURCE_DOCUMENTS:
        path = PLANNING_DIR / source["file"]
        docs.append(
            {
                **source,
                "digest_sha256": _file_digest(path),
                "source_use": "reviewed_planning_source_digest_only_no_private_context_no_runtime_probe",
            }
        )
    return docs


def build_aas_concept_gap_matrix(
    *, concept_rows: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Build the deterministic internal/admin AAS concept gap matrix."""

    rows = [dict(row) for row in (concept_rows or CONCEPT_ROWS)]
    _assert_rows(rows)

    safe_to_claim = [AAS_CONCEPT_GAP_MATRIX_SAFE_CLAIM]
    do_not_claim_yet = _dedupe(BLOCKED_CLAIMS)
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    matrix = {
        "schema": AAS_CONCEPT_GAP_MATRIX_SCHEMA,
        "matrix_id": AAS_CONCEPT_GAP_MATRIX_ID,
        "matrix_status": AAS_CONCEPT_GAP_MATRIX_STATUS,
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service and AAS concepts",
            "stopped_project_firewall": {
                "autojob_work_allowed": False,
                "frontier_academy_work_allowed": False,
                "kk_v2_work_allowed": False,
                "karmacadabra_v2_work_allowed": False,
            },
        },
        "source_documents": _source_documents(),
        "current_operator_state": {
            "explicit_operator_answer_available": False,
            "operator_approval_recorded": False,
            "answer_receipt_created": False,
            "recommended_no_human_posture": "pause_aas_proof_layering_or_keep_both_lanes_held",
            "reason": "June 5 final wrap says the useful next unit is an answer receipt only after a real explicit operator answer; this matrix is planning only.",
        },
        "readiness": dict(FALSE_FLAGS),
        "concept_gap_rows": rows,
        "cross_concept_rules": [
            "Do not add another no-answer or approval wrapper from this matrix.",
            "If no explicit human/operator answer exists, use this as a planning index only.",
            "If an explicit answer arrives later, create exactly one separate answer receipt before any product or runtime movement.",
            "Treat Field Asset Ops, Event Readiness, and Property Ops as concept-outline lanes until safer families have more proof.",
            "Keep exact GPS/raw metadata, private context, authority claims, public/customer/worker copy, pricing, dispatch, reputation, payment, runtime, and worker doctrine blocked.",
        ],
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "matrix_digest_sha256": "",
    }
    matrix["matrix_digest_sha256"] = _stable_digest(
        {k: v for k, v in matrix.items() if k != "matrix_digest_sha256"}
    )
    _assert_matrix_conservative(matrix)
    return matrix


def write_aas_concept_gap_matrix(*, artifact_dir: str | Path | None = None) -> Path:
    """Persist the deterministic AAS concept gap matrix."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    matrix = build_aas_concept_gap_matrix()
    path = base_dir / AAS_CONCEPT_GAP_MATRIX_FILENAME
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_concept_gap_matrix(*, artifact_dir: str | Path | None = None) -> dict[str, Any]:
    """Load the persisted AAS concept gap matrix."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    return json.loads((base_dir / AAS_CONCEPT_GAP_MATRIX_FILENAME).read_text(encoding="utf-8"))


def _assert_rows(rows: list[dict[str, Any]]) -> None:
    if len(rows) < 8:
        raise CityOpsContractError("AAS concept gap matrix requires broad concept coverage")
    families = {row.get("aas_family") for row in rows}
    required = {
        "retail_reality",
        "local_data_collection",
        "field_asset_ops",
        "event_readiness",
        "property_ops",
        "document_handoff",
        "compliance_desk",
        "incident_verification",
        "system_integration_runtime_memory",
    }
    missing = required - families
    if missing:
        raise CityOpsContractError(f"AAS concept gap matrix missing families: {sorted(missing)}")
    for row in rows:
        for key in [
            "source_backed_current_state",
            "small_safe_internal_admin_gap",
            "implementation_concept_expansion",
            "next_allowed_without_human_answer",
        ]:
            if not row.get(key):
                raise CityOpsContractError(f"AAS concept gap matrix row missing {key}")
        forbidden_values = {
            "approved",
            "customer_ready",
            "dispatch_ready",
            "runtime_ready",
            "public_ready",
        }
        if str(row.get("next_allowed_without_human_answer")) in forbidden_values:
            raise CityOpsContractError("AAS concept gap matrix row promotes without human answer")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    safe = set(safe_to_claim)
    blocked = set(do_not_claim_yet)
    if safe & blocked:
        raise CityOpsContractError(
            f"AAS concept gap matrix safe/blocked overlap: {sorted(safe & blocked)}"
        )
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS concept gap matrix forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing = set(BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS concept gap matrix missing blocked claims: {sorted(missing)}"
        )


def _assert_matrix_conservative(matrix: dict[str, Any]) -> None:
    if matrix.get("schema") != AAS_CONCEPT_GAP_MATRIX_SCHEMA:
        raise CityOpsContractError("AAS concept gap matrix schema drift")
    for key, expected in FALSE_FLAGS.items():
        if matrix["readiness"].get(key) is not expected:
            raise CityOpsContractError(f"AAS concept gap matrix readiness promoted {key}")
    state = matrix["current_operator_state"]
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS concept gap matrix operator state promoted {key}")
    firewall = matrix["governing_priority"]["stopped_project_firewall"]
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS concept gap matrix stopped-project firewall drift: {key}")
