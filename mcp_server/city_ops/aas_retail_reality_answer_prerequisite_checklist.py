"""Internal/admin Retail Reality answer prerequisite checklist.

This module consumes the AAS concept-gap implementation roadmap and renders the
rank-1 Retail Reality next move as a checklist of prerequisites that must be
satisfied before any separate answer/hold record can exist. It deliberately does
not record an operator answer, approval, answer receipt, customer/public/worker
copy, catalog/pricing/queue/dispatch surface, reputation signal, runtime/Acontext
mutation, exact-location/raw-metadata release, private-context release, domain
authority, or stopped-project integration.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_concept_gap_implementation_roadmap import (
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS,
    ROADMAP_BLOCKED_CLAIMS,
    load_aas_concept_gap_implementation_roadmap,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_SCHEMA = (
    "city_ops.aas_retail_reality_answer_prerequisite_checklist.v1"
)
AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_FILENAME = (
    "aas_retail_reality_answer_prerequisite_checklist.json"
)
AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_SAFE_CLAIM = (
    "internal_admin_aas_retail_reality_answer_prerequisite_checklist_landed"
)
AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_ID = (
    "execution_market.aas.retail_reality_answer_prerequisite_checklist.2026_06_06_0200"
)
AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_STATUS = (
    "internal_admin_prerequisite_checklist_no_answer_no_approval_no_product_or_runtime_promotion"
)

EXPECTED_RANK_ONE_SLICE = (
    "answer_receipt_prerequisite_checklist_only_if_explicit_operator_answer_arrives"
)

CHECKLIST_FALSE_FLAGS = {
    "checklist_records_operator_answer": False,
    "checklist_records_operator_approval": False,
    "checklist_creates_answer_receipt": False,
    "checklist_selects_future_answer": False,
    "checklist_treats_missing_answer_as_answer": False,
    "checklist_treats_prerequisite_as_approval": False,
    "checklist_approves_product_exposure": False,
    "checklist_creates_retail_reality_answer_or_hold_record": False,
    "checklist_creates_customer_copy": False,
    "checklist_creates_public_catalog_or_pricing_surface": False,
    "checklist_launches_queue_or_dispatch": False,
    "checklist_creates_worker_instruction": False,
    "checklist_emits_erc8004_reputation": False,
    "checklist_emits_worker_skill_dna": False,
    "checklist_reverifies_payment_or_production": False,
    "checklist_mutates_runtime_acontext_or_irc": False,
    "checklist_releases_exact_gps_or_raw_metadata": False,
    "checklist_releases_private_context": False,
    "checklist_grants_retail_legal_regulator_safety_or_sla_authority": False,
    "checklist_publishes_worker_copyable_doctrine": False,
    "checklist_integrates_or_expands_stopped_projects": False,
}

CHECKLIST_BLOCKED_CLAIMS = [
    *ROADMAP_BLOCKED_CLAIMS,
    "retail_reality_answer_prerequisite_checklist_records_operator_answer",
    "retail_reality_answer_prerequisite_checklist_records_operator_approval",
    "retail_reality_answer_prerequisite_checklist_creates_answer_receipt",
    "retail_reality_answer_prerequisite_checklist_selects_future_answer",
    "retail_reality_answer_prerequisite_checklist_treats_missing_answer_as_answer",
    "retail_reality_answer_prerequisite_checklist_treats_prerequisite_as_approval",
    "retail_reality_answer_prerequisite_checklist_approves_product_exposure",
    "retail_reality_answer_prerequisite_checklist_creates_retail_reality_answer_or_hold_record",
    "retail_reality_answer_prerequisite_checklist_creates_customer_public_or_worker_surface",
    "retail_reality_answer_prerequisite_checklist_authorizes_catalog_pricing_quote_route_queue_or_dispatch",
    "retail_reality_answer_prerequisite_checklist_creates_worker_instruction",
    "retail_reality_answer_prerequisite_checklist_emits_erc8004_reputation_or_worker_skill_dna",
    "retail_reality_answer_prerequisite_checklist_reverifies_payment_or_production",
    "retail_reality_answer_prerequisite_checklist_mutates_runtime_acontext_or_irc_session_manager",
    "retail_reality_answer_prerequisite_checklist_releases_exact_gps_raw_metadata_or_private_context",
    "retail_reality_answer_prerequisite_checklist_grants_retail_legal_regulator_safety_or_sla_authority",
    "retail_reality_answer_prerequisite_checklist_publishes_worker_copyable_doctrine",
    "retail_reality_answer_prerequisite_checklist_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(CHECKLIST_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "future_answer_selected",
    "retail_reality_answer_record_ready",
    "retail_reality_hold_record_ready",
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
    "raw_metadata_release_ready",
    "private_context_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "karmacadabra_v2_ready",
}

PREREQUISITE_ROWS = [
    {
        "key": "explicit_operator_answer",
        "prompt_for_future_operator": (
            "Choose exactly one explicit Retail Reality answer value in a separate answer record, "
            "or leave both lanes held."
        ),
        "required_before": "any_retail_reality_answer_or_hold_record",
        "accepted_future_values": [
            "create_retail_reality_answer_or_hold_record",
            "keep_both_lanes_held",
            "pause_aas_proof_layering",
        ],
        "missing_default": "keep_both_lanes_held",
    },
    {
        "key": "answer_source_trace",
        "prompt_for_future_operator": (
            "Identify the source message/session/date for the explicit answer without exposing "
            "private context in customer, worker, or public copy."
        ),
        "required_before": "answer_receipt_source_digest",
        "accepted_future_values": ["source_pointer_and_digest_only"],
        "missing_default": "no_answer_receipt",
    },
    {
        "key": "product_exposure_scope",
        "prompt_for_future_operator": (
            "Confirm whether the answer only permits an internal hold/answer record or separately "
            "permits product exposure."
        ),
        "required_before": "retail_reality_product_exposure_or_customer_copy",
        "accepted_future_values": [
            "internal_hold_record_only",
            "product_exposure_requires_separate_approval",
        ],
        "missing_default": "no_product_exposure",
    },
    {
        "key": "redaction_and_metadata_boundary",
        "prompt_for_future_operator": (
            "Confirm exact GPS, raw metadata, private context, and stream-sensitive details remain "
            "redacted from every non-internal surface."
        ),
        "required_before": "any_customer_public_worker_or_catalog_surface",
        "accepted_future_values": ["redacted_internal_digest_only"],
        "missing_default": "hold_all_external_surfaces",
    },
    {
        "key": "catalog_pricing_queue_dispatch_boundary",
        "prompt_for_future_operator": (
            "State separately whether catalog, pricing, quote, queue, or dispatch work is allowed; "
            "do not infer it from a Retail Reality answer."
        ),
        "required_before": "catalog_pricing_queue_or_dispatch_work",
        "accepted_future_values": ["separate_operator_approval_required"],
        "missing_default": "no_catalog_pricing_queue_or_dispatch",
    },
    {
        "key": "authority_language_boundary",
        "prompt_for_future_operator": (
            "Confirm Retail Reality language stays observational and never claims legal, regulator, "
            "safety, SLA, repair, warranty, insurance, or official authority."
        ),
        "required_before": "any_offer_copy_or_operator_summary",
        "accepted_future_values": ["observation_only_language"],
        "missing_default": "no_domain_authority_claims",
    },
    {
        "key": "runtime_and_cross_project_boundary",
        "prompt_for_future_operator": (
            "Confirm no runtime/Acontext/IRC mutation, cross-project autorouting, AutoJob, "
            "Frontier Academy, KK v2, or KarmaCadabra v2 expansion is bundled into this answer."
        ),
        "required_before": "any_runtime_or_cross_project_work",
        "accepted_future_values": ["not_in_scope_for_retail_reality_answer"],
        "missing_default": "no_runtime_or_stopped_project_work",
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


def _retail_reality_row(roadmap: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in roadmap.get("roadmap_rows", []) if row.get("aas_family") == "retail_reality"]
    if len(rows) != 1:
        raise CityOpsContractError("Retail Reality checklist source roadmap row missing or duplicated")
    row = rows[0]
    if row.get("planning_sequence_rank") != 1:
        raise CityOpsContractError("Retail Reality checklist source roadmap rank drift")
    if row.get("roadmap_next_planning_slice") != EXPECTED_RANK_ONE_SLICE:
        raise CityOpsContractError("Retail Reality checklist source roadmap next slice drift")
    if row.get("still_blocked") is not True:
        raise CityOpsContractError("Retail Reality checklist source roadmap unblocked retail reality")
    if row.get("required_gate_before_any_delivery_or_runtime_movement") != (
        "separate_explicit_operator_answer_receipt_then_specific_gate"
    ):
        raise CityOpsContractError("Retail Reality checklist source roadmap gate drift")
    return row


def _assert_source_roadmap(roadmap: dict[str, Any]) -> None:
    if roadmap.get("schema") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA:
        raise CityOpsContractError("Retail Reality checklist source roadmap schema drift")
    if roadmap.get("roadmap_status") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS:
        raise CityOpsContractError("Retail Reality checklist source roadmap status drift")
    safe = set(roadmap.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("Retail Reality checklist source roadmap safe claim missing")
    blocked = set(roadmap.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(ROADMAP_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"Retail Reality checklist source missing blocked claims: {sorted(missing)}"
        )
    state = roadmap.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"Retail Reality checklist source promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("Retail Reality checklist source selected future decision")
    firewall = roadmap.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"Retail Reality checklist source allowed {key}")
    _retail_reality_row(roadmap)


def _checklist_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(PREREQUISITE_ROWS, start=1):
        rows.append(
            {
                **row,
                "check_order": index,
                "satisfied_by_this_checklist": False,
                "creates_answer_or_approval": False,
                "allows_external_or_runtime_promotion": False,
                "if_missing": row["missing_default"],
            }
        )
    return rows


def build_aas_retail_reality_answer_prerequisite_checklist(
    *,
    artifact_dir: str | Path | None = None,
    source_roadmap: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin Retail Reality prerequisite checklist."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    roadmap = source_roadmap or load_aas_concept_gap_implementation_roadmap(
        artifact_dir=source_dir
    )
    _assert_source_roadmap(roadmap)
    retail_row = _retail_reality_row(roadmap)

    safe_to_claim = [
        AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
        AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_SAFE_CLAIM,
    ]
    do_not_claim_yet = _dedupe(CHECKLIST_BLOCKED_CLAIMS)

    checklist = {
        "schema": AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_SCHEMA,
        "checklist_id": AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_ID,
        "checklist_status": AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_STATUS,
        "source_roadmap": {
            "file": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
            "schema": roadmap["schema"],
            "roadmap_id": roadmap["roadmap_id"],
            "safe_claim": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
            "digest_sha256": _stable_digest(roadmap),
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service implementation planning",
            "stopped_project_firewall": dict(
                roadmap["governing_priority"]["stopped_project_firewall"]
            ),
        },
        "rank_one_source_row": {
            "aas_family": retail_row["aas_family"],
            "planning_sequence_rank": retail_row["planning_sequence_rank"],
            "roadmap_next_planning_slice": retail_row["roadmap_next_planning_slice"],
            "still_blocked": retail_row["still_blocked"],
            "required_gate_before_any_delivery_or_runtime_movement": retail_row[
                "required_gate_before_any_delivery_or_runtime_movement"
            ],
        },
        "current_operator_state": {
            "explicit_operator_answer_available": False,
            "operator_approval_recorded": False,
            "answer_receipt_created": False,
            "selected_decision": None,
            "recommended_no_human_posture": "keep_both_lanes_held",
        },
        "readiness": {
            "retail_reality_answer_prerequisite_checklist_landed": True,
            **CHECKLIST_FALSE_FLAGS,
        },
        "prerequisite_rows": _checklist_rows(),
        "answer_record_creation_rule": {
            "may_create_answer_or_hold_record_from_this_checklist": False,
            "minimum_future_inputs_required": [row["key"] for row in PREREQUISITE_ROWS],
            "future_answer_must_be_separate_artifact": True,
            "missing_answer_default": "keep_both_lanes_held",
            "checklist_is_not_operator_answer": True,
            "checklist_is_not_operator_approval": True,
        },
        "promotion_gates": {
            "customer_public_worker_surface": "blocked_until_separate_answer_and_specific_approval",
            "catalog_pricing_queue_dispatch": "blocked_until_separate_catalog_pricing_dispatch_approval",
            "runtime_acontext_irc": "blocked_until_separate_runtime_memory_answer_and_live_recheck",
            "reputation_worker_skill_dna": "blocked_until_actual_delivery_evidence_and_reputation_policy",
            "payment_or_production_reverification": "not_changed_by_this_checklist",
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "checklist_digest_sha256": "",
    }
    checklist["checklist_digest_sha256"] = _stable_digest(
        {k: v for k, v in checklist.items() if k != "checklist_digest_sha256"}
    )
    _assert_checklist_conservative(checklist, source_roadmap=roadmap)
    return checklist


def write_aas_retail_reality_answer_prerequisite_checklist(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Retail Reality answer prerequisite checklist."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    checklist = build_aas_retail_reality_answer_prerequisite_checklist(artifact_dir=base_dir)
    path = base_dir / AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_FILENAME
    path.write_text(json.dumps(checklist, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_retail_reality_answer_prerequisite_checklist(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Retail Reality prerequisite checklist."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    checklist = json.loads(
        (base_dir / AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_roadmap = load_aas_concept_gap_implementation_roadmap(artifact_dir=base_dir)
    _assert_checklist_conservative(checklist, source_roadmap=source_roadmap)
    return checklist


def _assert_checklist_conservative(
    checklist: dict[str, Any], *, source_roadmap: dict[str, Any]
) -> None:
    _assert_source_roadmap(source_roadmap)
    if checklist.get("schema") != AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_SCHEMA:
        raise CityOpsContractError("Retail Reality prerequisite checklist schema drift")
    if checklist.get("checklist_id") != AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_ID:
        raise CityOpsContractError("Retail Reality prerequisite checklist id drift")
    if checklist.get("checklist_status") != AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_STATUS:
        raise CityOpsContractError("Retail Reality prerequisite checklist status drift")
    source = checklist.get("source_roadmap", {})
    if source.get("digest_sha256") != _stable_digest(source_roadmap):
        raise CityOpsContractError("Retail Reality prerequisite checklist source digest drift")

    state = checklist.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"Retail Reality prerequisite checklist promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("Retail Reality prerequisite checklist selected future decision")

    readiness = checklist.get("readiness", {})
    if readiness.get("retail_reality_answer_prerequisite_checklist_landed") is not True:
        raise CityOpsContractError("Retail Reality prerequisite checklist landed flag missing")
    for key, expected in CHECKLIST_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(
                f"Retail Reality prerequisite checklist readiness promoted {key}"
            )

    rows = checklist.get("prerequisite_rows", [])
    if [row.get("check_order") for row in rows] != list(range(1, len(PREREQUISITE_ROWS) + 1)):
        raise CityOpsContractError("Retail Reality prerequisite checklist row order drift")
    expected_keys = [row["key"] for row in PREREQUISITE_ROWS]
    if [row.get("key") for row in rows] != expected_keys:
        raise CityOpsContractError("Retail Reality prerequisite checklist row key drift")
    for row in rows:
        if row.get("satisfied_by_this_checklist") is not False:
            raise CityOpsContractError("Retail Reality prerequisite checklist row satisfied early")
        if row.get("creates_answer_or_approval") is not False:
            raise CityOpsContractError("Retail Reality prerequisite checklist row creates answer")
        if row.get("allows_external_or_runtime_promotion") is not False:
            raise CityOpsContractError("Retail Reality prerequisite checklist row promotes externally")

    rule = checklist.get("answer_record_creation_rule", {})
    for key in [
        "may_create_answer_or_hold_record_from_this_checklist",
        "checklist_is_not_operator_answer",
        "checklist_is_not_operator_approval",
    ]:
        expected = False if key == "may_create_answer_or_hold_record_from_this_checklist" else True
        if rule.get(key) is not expected:
            raise CityOpsContractError(f"Retail Reality prerequisite checklist rule drift {key}")
    if rule.get("missing_answer_default") != "keep_both_lanes_held":
        raise CityOpsContractError("Retail Reality prerequisite checklist missing-answer default drift")

    source_row = checklist.get("rank_one_source_row", {})
    if source_row.get("aas_family") != "retail_reality":
        raise CityOpsContractError("Retail Reality prerequisite checklist source row family drift")
    if source_row.get("roadmap_next_planning_slice") != EXPECTED_RANK_ONE_SLICE:
        raise CityOpsContractError("Retail Reality prerequisite checklist source row slice drift")
    if source_row.get("still_blocked") is not True:
        raise CityOpsContractError("Retail Reality prerequisite checklist source row unblocked")

    safe = set(checklist.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(checklist.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_RETAIL_REALITY_ANSWER_PREREQUISITE_CHECKLIST_SAFE_CLAIM not in safe:
        raise CityOpsContractError("Retail Reality prerequisite checklist safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"Retail Reality prerequisite checklist forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(CHECKLIST_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"Retail Reality prerequisite checklist missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"Retail Reality prerequisite checklist claim overlap: {sorted(overlap)}"
        )

    firewall = checklist.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"Retail Reality prerequisite checklist allowed {key}")
