"""Internal/admin Field Asset Ops visible-state fixture outline.

This slice consumes the AAS concept-gap implementation roadmap and expands only
its rank-4 Field Asset Ops concept outline action. It is deliberately not an
operator answer, approval record, answer receipt, customer/worker/public copy,
inspection result, repair instruction, SLA/warranty/safety claim, or runtime
movement.
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

AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SCHEMA = (
    "city_ops.aas_field_asset_visible_state_fixture_outline.v1"
)
AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_FILENAME = (
    "aas_field_asset_visible_state_fixture_outline.json"
)
AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM = (
    "internal_admin_aas_field_asset_visible_state_fixture_outline_landed"
)
AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_ID = (
    "execution_market.aas.field_asset_visible_state_fixture_outline.2026_06_06_0400"
)
AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_STATUS = (
    "internal_admin_concept_outline_no_answer_no_approval_no_repair_sla_or_customer_copy"
)

FALSE_FLAGS = {
    "outline_records_operator_answer": False,
    "outline_records_operator_approval": False,
    "outline_creates_answer_receipt": False,
    "outline_selects_future_answer": False,
    "outline_approves_product_exposure": False,
    "outline_creates_customer_public_or_worker_copy": False,
    "outline_authorizes_field_visit_access_or_recipient": False,
    "outline_authorizes_inspection_repair_or_remediation": False,
    "outline_certifies_asset_functionality_safety_warranty_or_sla": False,
    "outline_creates_public_catalog_pricing_quote_or_route": False,
    "outline_launches_queue_dispatch_or_worker_instruction": False,
    "outline_emits_reputation_or_worker_skill_dna": False,
    "outline_reverifies_payment_or_production": False,
    "outline_mutates_runtime_acontext_or_irc": False,
    "outline_exposes_exact_gps_raw_metadata_private_context_or_pii": False,
    "outline_grants_property_access_appraisal_or_maintenance_authority": False,
    "outline_publishes_worker_copyable_doctrine": False,
    "outline_integrates_or_expands_stopped_projects": False,
}

VISIBLE_STATE_FIELDS = [
    "asset_identifier_placeholder_without_private_location",
    "visible_presence_or_absence_observed",
    "apparent_access_or_obstruction_observed",
    "apparent_surface_condition_observed",
    "visible_indicator_state_observed_without_functionality_certification",
    "photo_or_screenshot_reference_placeholder_after_redaction_review",
    "unknowns_and_unresolved_observations",
]

OBSERVATION_BOUNDARIES = [
    "record_only_visible_state_not_root_cause_or_repair_diagnosis",
    "separate_visibility_from_functionality_safety_warranty_and_sla",
    "do_not_infer property_access_permission_or_operator_authority",
    "do_not_publish exact_location_private_context_raw_metadata_or_pii",
    "customer_or_worker_copy_requires_separate_explicit_answer_receipt",
]

SAFE_LANGUAGE = [
    "visible asset state outline only",
    "repair and SLA language blocked",
    "functionality not certified",
    "access or safety authority not claimed",
    "future answer receipt required before field operation or customer use",
]

FORBIDDEN_LANGUAGE = [
    "repair required",
    "safe to operate",
    "SLA met",
    "warranty valid",
    "technician dispatched",
    "asset certified",
    "customer ready",
]

FIELD_ASSET_VISIBLE_STATE_BLOCKED_CLAIMS = [
    *ROADMAP_BLOCKED_CLAIMS,
    "field_asset_visible_state_outline_records_operator_answer",
    "field_asset_visible_state_outline_records_operator_approval",
    "field_asset_visible_state_outline_creates_answer_receipt",
    "field_asset_visible_state_outline_selects_future_answer",
    "field_asset_visible_state_outline_treats_concept_as_approval",
    "field_asset_visible_state_outline_approves_product_exposure",
    "field_asset_visible_state_outline_creates_customer_public_or_worker_copy",
    "field_asset_visible_state_outline_authorizes_field_visit_access_recipient_or_customer_use",
    "field_asset_visible_state_outline_authorizes_inspection_repair_remediation_or_maintenance",
    "field_asset_visible_state_outline_certifies_functionality_safety_warranty_or_sla",
    "field_asset_visible_state_outline_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "field_asset_visible_state_outline_creates_worker_instruction",
    "field_asset_visible_state_outline_emits_erc8004_reputation_or_worker_skill_dna",
    "field_asset_visible_state_outline_reverifies_payment_or_production",
    "field_asset_visible_state_outline_mutates_runtime_acontext_or_irc_session_manager",
    "field_asset_visible_state_outline_releases_exact_gps_raw_metadata_private_context_or_pii",
    "field_asset_visible_state_outline_grants_property_access_appraisal_or_maintenance_authority",
    "field_asset_visible_state_outline_publishes_worker_copyable_doctrine",
    "field_asset_visible_state_outline_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(FIELD_ASSET_VISIBLE_STATE_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "field_asset_ops_approved",
    "field_asset_ops_customer_ready",
    "field_visit_authorized",
    "repair_authorized",
    "remediation_authorized",
    "asset_functionality_certified",
    "asset_safety_certified",
    "warranty_ready",
    "sla_ready",
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


def _field_asset_row(roadmap: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in roadmap.get("roadmap_rows", [])
        if row.get("aas_family") == "field_asset_ops"
    ]
    if len(rows) != 1:
        raise CityOpsContractError("AAS field asset outline source row missing")
    row = rows[0]
    if row.get("planning_sequence_rank") != 4:
        raise CityOpsContractError("AAS field asset outline source rank drift")
    if row.get("roadmap_next_planning_slice") != (
        "visible_asset_state_fixture_outline_no_repair_or_sla_language"
    ):
        raise CityOpsContractError("AAS field asset outline source action drift")
    if row.get("still_blocked") is not True:
        raise CityOpsContractError("AAS field asset outline source row unblocked")
    if row.get("next_allowed_without_human_answer") != "concept_outline_only":
        raise CityOpsContractError("AAS field asset outline source concept mode drift")
    return row


def _assert_source_roadmap(roadmap: dict[str, Any]) -> None:
    if roadmap.get("schema") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA:
        raise CityOpsContractError("AAS field asset outline source schema drift")
    if roadmap.get("roadmap_status") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS:
        raise CityOpsContractError("AAS field asset outline source status drift")
    safe = set(roadmap.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS field asset outline source safe claim missing")
    blocked = set(roadmap.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(ROADMAP_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS field asset outline source missing blocked claims: {sorted(missing)}"
        )
    state = roadmap.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS field asset outline source promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS field asset outline source selected decision")
    _field_asset_row(roadmap)
    firewall = roadmap.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS field asset outline source allowed {key}")


def build_aas_field_asset_visible_state_fixture_outline(
    *,
    artifact_dir: str | Path | None = None,
    source_roadmap: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative Field Asset Ops visible-state fixture outline."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    roadmap = source_roadmap or load_aas_concept_gap_implementation_roadmap(
        artifact_dir=source_dir
    )
    _assert_source_roadmap(roadmap)
    row = _field_asset_row(roadmap)

    outline = {
        "schema": AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SCHEMA,
        "fixture_outline_id": AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_ID,
        "fixture_outline_status": AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_STATUS,
        "source_roadmap": {
            "file": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
            "schema": roadmap["schema"],
            "roadmap_id": roadmap["roadmap_id"],
            "safe_claim": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
            "digest_sha256": _stable_digest(roadmap),
            "consumed_row_family": "field_asset_ops",
            "consumed_row_rank": row["planning_sequence_rank"],
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service Field Asset Ops planning",
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
            "recommended_no_human_posture": "concept_outline_only",
        },
        "readiness": dict(FALSE_FLAGS),
        "field_asset_visible_state_fixture_outline": {
            "aas_family": "field_asset_ops",
            "allowed_use": "internal_admin_visible_asset_state_fixture_outline_no_repair_or_sla_language",
            "source_backed_current_state": row["source_backed_current_state"],
            "implementation_concept_expansion": row["implementation_concept_expansion"],
            "roadmap_next_planning_slice": row["roadmap_next_planning_slice"],
            "concept_mode": row["next_allowed_without_human_answer"],
            "visible_state_fields": list(VISIBLE_STATE_FIELDS),
            "observation_boundaries": list(OBSERVATION_BOUNDARIES),
            "safe_internal_language": list(SAFE_LANGUAGE),
            "forbidden_language": list(FORBIDDEN_LANGUAGE),
            "next_gate_before_any_delivery_or_runtime_movement": "separate_explicit_operator_answer_receipt_then_field_asset_ops_customer_or_dispatch_gate",
            "still_blocked": True,
        },
        "sequence_rules": [
            "Treat this outline as an internal/admin concept fixture only, never as approval or customer copy.",
            "Do not authorize field visit access, inspection, repair, remediation, warranty, safety, or SLA language from this outline.",
            "Do not convert visible-state observations into functionality certification or dispatch readiness.",
            "Create a separate explicit answer receipt before any Field Asset Ops customer, worker, field, or dispatch gate.",
            "Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.",
        ],
        "claim_boundaries": {
            "safe_to_claim": [
                AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
                AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(FIELD_ASSET_VISIBLE_STATE_BLOCKED_CLAIMS),
        },
        "fixture_outline_digest_sha256": "",
    }
    outline["fixture_outline_digest_sha256"] = _stable_digest(
        {k: v for k, v in outline.items() if k != "fixture_outline_digest_sha256"}
    )
    _assert_fixture_outline_conservative(outline, source_roadmap=roadmap)
    return outline


def write_aas_field_asset_visible_state_fixture_outline(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Field Asset Ops visible-state fixture outline."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    outline = build_aas_field_asset_visible_state_fixture_outline(artifact_dir=base_dir)
    path = base_dir / AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_FILENAME
    path.write_text(json.dumps(outline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_field_asset_visible_state_fixture_outline(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Field Asset Ops fixture outline."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    outline = json.loads(
        (base_dir / AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_roadmap = load_aas_concept_gap_implementation_roadmap(artifact_dir=base_dir)
    _assert_fixture_outline_conservative(outline, source_roadmap=source_roadmap)
    return outline


def _assert_fixture_outline_conservative(
    outline: dict[str, Any], *, source_roadmap: dict[str, Any]
) -> None:
    _assert_source_roadmap(source_roadmap)
    if outline.get("schema") != AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SCHEMA:
        raise CityOpsContractError("AAS field asset outline schema drift")
    if outline.get("fixture_outline_id") != AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_ID:
        raise CityOpsContractError("AAS field asset outline id drift")
    if outline.get("fixture_outline_status") != AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_STATUS:
        raise CityOpsContractError("AAS field asset outline status drift")
    source = outline.get("source_roadmap", {})
    if source.get("digest_sha256") != _stable_digest(source_roadmap):
        raise CityOpsContractError("AAS field asset outline source digest drift")
    if source.get("consumed_row_family") != "field_asset_ops" or source.get(
        "consumed_row_rank"
    ) != 4:
        raise CityOpsContractError("AAS field asset outline consumed wrong row")

    state = outline.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(
                f"AAS field asset outline operator state promoted {key}"
            )
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS field asset outline selected future decision")

    for key, expected in FALSE_FLAGS.items():
        if outline.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS field asset outline readiness promoted {key}")

    fixture = outline.get("field_asset_visible_state_fixture_outline", {})
    if fixture.get("aas_family") != "field_asset_ops":
        raise CityOpsContractError("AAS field asset outline family drift")
    if fixture.get("allowed_use") != "internal_admin_visible_asset_state_fixture_outline_no_repair_or_sla_language":
        raise CityOpsContractError("AAS field asset outline use drift")
    if fixture.get("concept_mode") != "concept_outline_only":
        raise CityOpsContractError("AAS field asset outline concept mode drift")
    if fixture.get("still_blocked") is not True:
        raise CityOpsContractError("AAS field asset outline unblocked")
    if fixture.get("next_gate_before_any_delivery_or_runtime_movement") != (
        "separate_explicit_operator_answer_receipt_then_field_asset_ops_customer_or_dispatch_gate"
    ):
        raise CityOpsContractError("AAS field asset outline next gate drift")
    if set(VISIBLE_STATE_FIELDS) - set(fixture.get("visible_state_fields", [])):
        raise CityOpsContractError("AAS field asset outline missing visible-state fields")
    if set(OBSERVATION_BOUNDARIES) - set(fixture.get("observation_boundaries", [])):
        raise CityOpsContractError("AAS field asset outline missing observation boundaries")
    if set(FORBIDDEN_LANGUAGE) - set(fixture.get("forbidden_language", [])):
        raise CityOpsContractError("AAS field asset outline missing forbidden language")
    for forbidden in ["repair required", "safe to operate", "customer ready"]:
        if forbidden in set(fixture.get("safe_internal_language", [])):
            raise CityOpsContractError("AAS field asset outline safe language promoted")

    safe = set(outline.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(outline.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS field asset outline safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS field asset outline forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(FIELD_ASSET_VISIBLE_STATE_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS field asset outline missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"AAS field asset outline claim overlap: {sorted(overlap)}"
        )

    firewall = outline.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS field asset outline allowed {key}")
