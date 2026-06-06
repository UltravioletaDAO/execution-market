"""Internal/admin Compliance Desk delivery-path hold gap review.

This slice consumes the AAS concept-gap implementation roadmap and expands only
its rank-3 Compliance Desk maintenance action. It is deliberately not an
operator answer, approval record, answer receipt, customer/worker/public copy,
publication route, regulator/legal sufficiency claim, or runtime movement.
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

AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_SCHEMA = (
    "city_ops.aas_compliance_desk_delivery_path_hold_gap_review.v1"
)
AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_FILENAME = (
    "aas_compliance_desk_delivery_path_hold_gap_review.json"
)
AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_SAFE_CLAIM = (
    "internal_admin_aas_compliance_desk_delivery_path_hold_gap_review_landed"
)
AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_ID = (
    "execution_market.aas.compliance_desk_delivery_path_hold_gap_review.2026_06_06_0100"
)
AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_STATUS = (
    "internal_admin_hold_gap_review_no_answer_no_approval_no_customer_copy_or_publication"
)

FALSE_FLAGS = {
    "hold_review_records_operator_answer": False,
    "hold_review_records_operator_approval": False,
    "hold_review_creates_answer_receipt": False,
    "hold_review_selects_future_answer": False,
    "hold_review_approves_product_exposure": False,
    "hold_review_creates_customer_public_or_worker_copy": False,
    "hold_review_authorizes_delivery_path_or_recipient": False,
    "hold_review_authorizes_publication_route": False,
    "hold_review_creates_public_catalog_pricing_quote_or_route": False,
    "hold_review_launches_queue_dispatch_or_worker_instruction": False,
    "hold_review_emits_reputation_or_worker_skill_dna": False,
    "hold_review_reverifies_payment_or_production": False,
    "hold_review_mutates_runtime_acontext_or_irc": False,
    "hold_review_exposes_exact_gps_raw_metadata_private_context_or_pii": False,
    "hold_review_grants_legal_regulator_inspection_or_acceptance_authority": False,
    "hold_review_publishes_worker_copyable_doctrine": False,
    "hold_review_integrates_or_expands_stopped_projects": False,
}

DELIVERY_HOLD_REASONS = [
    "authorized_recipient_or_review_role_not_selected",
    "authorized_delivery_channel_not_selected",
    "publication_route_not_approved",
    "customer_facing_format_not_approved",
    "legal_or_regulator_review_scope_not_authorized",
    "acceptance_or_sufficiency_criteria_not_recorded",
    "redaction_review_for_notice_evidence_not_authorized",
]

NOTICE_PACKAGING_BOUNDARIES = [
    "visible_notice_fields_may_be_described_only_as_observed_if_later_authorized",
    "source_type_must_remain_split_between_observed_documented_and_heard",
    "legibility_or_obstruction_notes_do_not_equal_legal_noncompliance",
    "operator_review_notice_must_survive_before_any_future_customer_copy",
    "public_or_regulator_submission_path_requires_separate_explicit_answer_receipt",
]

SAFE_LANGUAGE = [
    "visible notice state not yet customer-deliverable",
    "delivery path remains held",
    "publication route not authorized",
    "regulator or legal acceptance not claimed",
    "future answer receipt required before customer or public use",
]

FORBIDDEN_LANGUAGE = [
    "legally compliant",
    "regulator accepted",
    "official inspection passed",
    "customer ready",
    "publish this notice report",
    "deliver to customer",
    "public catalog ready",
]

COMPLIANCE_DESK_HOLD_GAP_BLOCKED_CLAIMS = [
    *ROADMAP_BLOCKED_CLAIMS,
    "compliance_desk_hold_gap_review_records_operator_answer",
    "compliance_desk_hold_gap_review_records_operator_approval",
    "compliance_desk_hold_gap_review_creates_answer_receipt",
    "compliance_desk_hold_gap_review_selects_future_answer",
    "compliance_desk_hold_gap_review_treats_maintenance_as_approval",
    "compliance_desk_hold_gap_review_approves_product_exposure",
    "compliance_desk_hold_gap_review_creates_customer_public_or_worker_copy",
    "compliance_desk_hold_gap_review_authorizes_recipient_channel_delivery_or_acceptance",
    "compliance_desk_hold_gap_review_authorizes_publication_or_regulator_submission_route",
    "compliance_desk_hold_gap_review_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "compliance_desk_hold_gap_review_creates_worker_instruction",
    "compliance_desk_hold_gap_review_emits_erc8004_reputation_or_worker_skill_dna",
    "compliance_desk_hold_gap_review_reverifies_payment_or_production",
    "compliance_desk_hold_gap_review_mutates_runtime_acontext_or_irc_session_manager",
    "compliance_desk_hold_gap_review_releases_exact_gps_raw_metadata_private_context_or_pii",
    "compliance_desk_hold_gap_review_grants_legal_regulator_inspection_sufficiency_or_acceptance_authority",
    "compliance_desk_hold_gap_review_publishes_worker_copyable_doctrine",
    "compliance_desk_hold_gap_review_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(COMPLIANCE_DESK_HOLD_GAP_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "compliance_desk_approved",
    "compliance_desk_customer_ready",
    "compliance_desk_delivery_authorized",
    "compliance_desk_publication_authorized",
    "compliance_desk_legal_ready",
    "compliance_desk_regulator_ready",
    "compliance_desk_official_inspection_ready",
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
    "gps_release_ready",
    "private_context_release_ready",
    "pii_release_ready",
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


def _compliance_desk_row(roadmap: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in roadmap.get("roadmap_rows", [])
        if row.get("aas_family") == "compliance_desk"
    ]
    if len(rows) != 1:
        raise CityOpsContractError("AAS compliance desk hold gap source row missing")
    row = rows[0]
    if row.get("planning_sequence_rank") != 3:
        raise CityOpsContractError("AAS compliance desk hold gap source rank drift")
    if row.get("roadmap_next_planning_slice") != (
        "delivery_path_hold_gap_review_without_customer_copy"
    ):
        raise CityOpsContractError("AAS compliance desk hold gap source action drift")
    if row.get("still_blocked") is not True:
        raise CityOpsContractError("AAS compliance desk hold gap source row unblocked")
    if row.get("next_allowed_without_human_answer") != "maintenance_only_no_delivery_path":
        raise CityOpsContractError("AAS compliance desk hold gap source maintenance drift")
    return row


def _assert_source_roadmap(roadmap: dict[str, Any]) -> None:
    if roadmap.get("schema") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA:
        raise CityOpsContractError("AAS compliance desk hold gap source schema drift")
    if roadmap.get("roadmap_status") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS:
        raise CityOpsContractError("AAS compliance desk hold gap source status drift")
    safe = set(roadmap.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS compliance desk hold gap source safe claim missing")
    blocked = set(roadmap.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(ROADMAP_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS compliance desk hold gap source missing blocked claims: {sorted(missing)}"
        )
    state = roadmap.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS compliance desk hold gap source promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS compliance desk hold gap source selected decision")
    _compliance_desk_row(roadmap)
    firewall = roadmap.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS compliance desk hold gap source allowed {key}")


def build_aas_compliance_desk_delivery_path_hold_gap_review(
    *,
    artifact_dir: str | Path | None = None,
    source_roadmap: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative Compliance Desk delivery-path hold gap review."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    roadmap = source_roadmap or load_aas_concept_gap_implementation_roadmap(
        artifact_dir=source_dir
    )
    _assert_source_roadmap(roadmap)
    row = _compliance_desk_row(roadmap)

    review = {
        "schema": AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_SCHEMA,
        "hold_gap_review_id": AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_ID,
        "hold_gap_review_status": AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_STATUS,
        "source_roadmap": {
            "file": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
            "schema": roadmap["schema"],
            "roadmap_id": roadmap["roadmap_id"],
            "safe_claim": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
            "digest_sha256": _stable_digest(roadmap),
            "consumed_row_family": "compliance_desk",
            "consumed_row_rank": row["planning_sequence_rank"],
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service Compliance Desk planning",
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
            "recommended_no_human_posture": "maintenance_only_no_delivery_path",
        },
        "readiness": dict(FALSE_FLAGS),
        "compliance_desk_hold_gap_review": {
            "aas_family": "compliance_desk",
            "allowed_use": "internal_admin_delivery_path_hold_gap_review_without_customer_copy",
            "source_backed_current_state": row["source_backed_current_state"],
            "implementation_concept_expansion": row["implementation_concept_expansion"],
            "roadmap_next_planning_slice": row["roadmap_next_planning_slice"],
            "maintenance_mode": row["next_allowed_without_human_answer"],
            "delivery_hold_reasons": list(DELIVERY_HOLD_REASONS),
            "notice_packaging_boundaries": list(NOTICE_PACKAGING_BOUNDARIES),
            "safe_internal_language": list(SAFE_LANGUAGE),
            "forbidden_language": list(FORBIDDEN_LANGUAGE),
            "next_gate_before_any_delivery_or_runtime_movement": "separate_explicit_operator_answer_receipt_then_compliance_desk_delivery_publication_gate",
            "still_blocked": True,
        },
        "sequence_rules": [
            "Treat this review as a hold-gap maintenance artifact only, never as approval or customer copy.",
            "Do not authorize recipient, delivery channel, publication route, customer format, legal/regulator review, acceptance, or sufficiency from this review.",
            "Do not convert visible notice observations into legal compliance, official inspection, or regulator acceptance language.",
            "Create a separate explicit answer receipt before any Compliance Desk delivery/publication gate.",
            "Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.",
        ],
        "claim_boundaries": {
            "safe_to_claim": [
                AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
                AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(COMPLIANCE_DESK_HOLD_GAP_BLOCKED_CLAIMS),
        },
        "hold_gap_review_digest_sha256": "",
    }
    review["hold_gap_review_digest_sha256"] = _stable_digest(
        {k: v for k, v in review.items() if k != "hold_gap_review_digest_sha256"}
    )
    _assert_hold_gap_review_conservative(review, source_roadmap=roadmap)
    return review


def write_aas_compliance_desk_delivery_path_hold_gap_review(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Compliance Desk delivery-path hold gap review."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    review = build_aas_compliance_desk_delivery_path_hold_gap_review(artifact_dir=base_dir)
    path = base_dir / AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_FILENAME
    path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_compliance_desk_delivery_path_hold_gap_review(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Compliance Desk hold gap review."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    review = json.loads(
        (base_dir / AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_roadmap = load_aas_concept_gap_implementation_roadmap(artifact_dir=base_dir)
    _assert_hold_gap_review_conservative(review, source_roadmap=source_roadmap)
    return review


def _assert_hold_gap_review_conservative(
    review: dict[str, Any], *, source_roadmap: dict[str, Any]
) -> None:
    _assert_source_roadmap(source_roadmap)
    if review.get("schema") != AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_SCHEMA:
        raise CityOpsContractError("AAS compliance desk hold gap review schema drift")
    if review.get("hold_gap_review_id") != AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_ID:
        raise CityOpsContractError("AAS compliance desk hold gap review id drift")
    if review.get("hold_gap_review_status") != AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_STATUS:
        raise CityOpsContractError("AAS compliance desk hold gap review status drift")
    source = review.get("source_roadmap", {})
    if source.get("digest_sha256") != _stable_digest(source_roadmap):
        raise CityOpsContractError("AAS compliance desk hold gap review source digest drift")
    if source.get("consumed_row_family") != "compliance_desk" or source.get(
        "consumed_row_rank"
    ) != 3:
        raise CityOpsContractError("AAS compliance desk hold gap review consumed wrong row")

    state = review.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(
                f"AAS compliance desk hold gap review operator state promoted {key}"
            )
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS compliance desk hold gap review selected future decision")

    for key, expected in FALSE_FLAGS.items():
        if review.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS compliance desk hold gap review readiness promoted {key}")

    gap = review.get("compliance_desk_hold_gap_review", {})
    if gap.get("aas_family") != "compliance_desk":
        raise CityOpsContractError("AAS compliance desk hold gap review family drift")
    if gap.get("allowed_use") != "internal_admin_delivery_path_hold_gap_review_without_customer_copy":
        raise CityOpsContractError("AAS compliance desk hold gap review use drift")
    if gap.get("maintenance_mode") != "maintenance_only_no_delivery_path":
        raise CityOpsContractError("AAS compliance desk hold gap review maintenance mode drift")
    if gap.get("still_blocked") is not True:
        raise CityOpsContractError("AAS compliance desk hold gap review unblocked")
    if gap.get("next_gate_before_any_delivery_or_runtime_movement") != (
        "separate_explicit_operator_answer_receipt_then_compliance_desk_delivery_publication_gate"
    ):
        raise CityOpsContractError("AAS compliance desk hold gap review next gate drift")
    if set(DELIVERY_HOLD_REASONS) - set(gap.get("delivery_hold_reasons", [])):
        raise CityOpsContractError("AAS compliance desk hold gap review missing hold reasons")
    if set(NOTICE_PACKAGING_BOUNDARIES) - set(gap.get("notice_packaging_boundaries", [])):
        raise CityOpsContractError("AAS compliance desk hold gap review missing notice boundaries")
    if set(FORBIDDEN_LANGUAGE) - set(gap.get("forbidden_language", [])):
        raise CityOpsContractError("AAS compliance desk hold gap review missing forbidden language")
    for forbidden in ["customer ready", "deliver to customer", "legally compliant"]:
        if forbidden in set(gap.get("safe_internal_language", [])):
            raise CityOpsContractError("AAS compliance desk hold gap review safe language promoted")

    safe = set(review.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(review.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_COMPLIANCE_DESK_DELIVERY_PATH_HOLD_GAP_REVIEW_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS compliance desk hold gap review safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS compliance desk hold gap review forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(COMPLIANCE_DESK_HOLD_GAP_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS compliance desk hold gap review missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"AAS compliance desk hold gap review claim overlap: {sorted(overlap)}"
        )

    firewall = review.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS compliance desk hold gap review allowed {key}")
