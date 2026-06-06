"""Internal/admin Event Readiness observation outline.

This slice consumes the AAS concept-gap implementation roadmap and expands only
its rank-5 Event Readiness concept outline action. It is deliberately not an
operator answer, approval record, answer receipt, customer/worker/public copy,
permit review, security plan, attendance guarantee, vendor commitment, venue
authority, route/queue/dispatch surface, or runtime movement.
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

AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SCHEMA = (
    "city_ops.aas_event_readiness_observation_outline.v1"
)
AAS_EVENT_READINESS_OBSERVATION_OUTLINE_FILENAME = (
    "aas_event_readiness_observation_outline.json"
)
AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM = (
    "internal_admin_aas_event_readiness_observation_outline_landed"
)
AAS_EVENT_READINESS_OBSERVATION_OUTLINE_ID = (
    "execution_market.aas.event_readiness_observation_outline.2026_06_06_0700"
)
AAS_EVENT_READINESS_OBSERVATION_OUTLINE_STATUS = (
    "internal_admin_concept_outline_no_answer_no_approval_no_permit_security_or_outcome_claim"
)

FALSE_FLAGS = {
    "outline_records_operator_answer": False,
    "outline_records_operator_approval": False,
    "outline_creates_answer_receipt": False,
    "outline_selects_future_answer": False,
    "outline_approves_product_exposure": False,
    "outline_creates_customer_public_or_worker_copy": False,
    "outline_authorizes_event_site_access_or_recipient": False,
    "outline_authorizes_permit_security_vendor_or_venue_decision": False,
    "outline_certifies_capacity_safety_attendance_outcome_or_sla": False,
    "outline_creates_public_catalog_pricing_quote_or_route": False,
    "outline_launches_queue_dispatch_or_worker_instruction": False,
    "outline_emits_reputation_or_worker_skill_dna": False,
    "outline_reverifies_payment_or_production": False,
    "outline_mutates_runtime_acontext_or_irc": False,
    "outline_exposes_exact_gps_raw_metadata_private_context_or_pii": False,
    "outline_grants_municipal_permit_legal_or_crowd_control_authority": False,
    "outline_publishes_worker_copyable_doctrine": False,
    "outline_integrates_or_expands_stopped_projects": False,
}

OBSERVATION_FIELDS = [
    "event_identifier_placeholder_without_private_location",
    "scheduled_window_placeholder_without_contact_or_private_context",
    "visible_setup_presence_or_absence_observed",
    "apparent_staging_or_wayfinding_state_observed",
    "apparent_access_or_obstruction_observed_without_access_authority",
    "visible_vendor_or_equipment_presence_observed_without_performance_claim",
    "photo_or_screenshot_reference_placeholder_after_redaction_review",
    "unknowns_and_unresolved_observations",
]

OBSERVATION_BOUNDARIES = [
    "record_only_visible_pre_event_state_not_permit_security_or_outcome_authority",
    "separate_setup_observation_from_capacity_safety_crowd_control_and_sla",
    "do_not_infer_venue_access_vendor_commitment_or_operator_authority",
    "do_not_publish_exact_location_private_context_raw_metadata_or_pii",
    "customer_or_worker_copy_requires_separate_explicit_answer_receipt",
]

SAFE_LANGUAGE = [
    "visible event-readiness observation outline only",
    "permit security and outcome claims blocked",
    "visible setup does not certify operational readiness",
    "venue vendor and crowd-control authority not claimed",
    "future answer receipt required before event delivery or customer use",
]

FORBIDDEN_LANGUAGE = [
    "permit approved",
    "security cleared",
    "event guaranteed",
    "crowd safety confirmed",
    "vendor confirmed",
    "venue authorized",
    "attendee ready",
    "dispatch ready",
]

EVENT_READINESS_OBSERVATION_BLOCKED_CLAIMS = [
    *ROADMAP_BLOCKED_CLAIMS,
    "event_readiness_observation_outline_records_operator_answer",
    "event_readiness_observation_outline_records_operator_approval",
    "event_readiness_observation_outline_creates_answer_receipt",
    "event_readiness_observation_outline_selects_future_answer",
    "event_readiness_observation_outline_treats_concept_as_approval",
    "event_readiness_observation_outline_approves_product_exposure",
    "event_readiness_observation_outline_creates_customer_public_or_worker_copy",
    "event_readiness_observation_outline_authorizes_event_site_access_recipient_or_customer_use",
    "event_readiness_observation_outline_authorizes_permit_security_vendor_venue_or_crowd_control_decision",
    "event_readiness_observation_outline_certifies_capacity_safety_attendance_outcome_or_sla",
    "event_readiness_observation_outline_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "event_readiness_observation_outline_creates_worker_instruction",
    "event_readiness_observation_outline_emits_erc8004_reputation_or_worker_skill_dna",
    "event_readiness_observation_outline_reverifies_payment_or_production",
    "event_readiness_observation_outline_mutates_runtime_acontext_or_irc_session_manager",
    "event_readiness_observation_outline_releases_exact_gps_raw_metadata_private_context_or_pii",
    "event_readiness_observation_outline_grants_municipal_permit_legal_or_crowd_control_authority",
    "event_readiness_observation_outline_publishes_worker_copyable_doctrine",
    "event_readiness_observation_outline_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(EVENT_READINESS_OBSERVATION_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "event_readiness_approved",
    "event_readiness_customer_ready",
    "event_site_access_authorized",
    "permit_approved",
    "security_cleared",
    "vendor_confirmed",
    "venue_authorized",
    "capacity_certified",
    "crowd_safety_certified",
    "attendance_outcome_guaranteed",
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


def _event_readiness_row(roadmap: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in roadmap.get("roadmap_rows", [])
        if row.get("aas_family") == "event_readiness"
    ]
    if len(rows) != 1:
        raise CityOpsContractError("AAS event readiness outline source row missing")
    row = rows[0]
    if row.get("planning_sequence_rank") != 5:
        raise CityOpsContractError("AAS event readiness outline source rank drift")
    if row.get("roadmap_next_planning_slice") != (
        "observed_pre_event_blocker_outline_no_permit_security_or_outcome_claim"
    ):
        raise CityOpsContractError("AAS event readiness outline source action drift")
    if row.get("still_blocked") is not True:
        raise CityOpsContractError("AAS event readiness outline source row unblocked")
    if row.get("next_allowed_without_human_answer") != "concept_outline_only":
        raise CityOpsContractError("AAS event readiness outline source concept mode drift")
    return row


def _assert_source_roadmap(roadmap: dict[str, Any]) -> None:
    if roadmap.get("schema") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA:
        raise CityOpsContractError("AAS event readiness outline source schema drift")
    if roadmap.get("roadmap_status") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS:
        raise CityOpsContractError("AAS event readiness outline source status drift")
    safe = set(roadmap.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS event readiness outline source safe claim missing")
    blocked = set(roadmap.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(ROADMAP_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS event readiness outline source missing blocked claims: {sorted(missing)}"
        )
    state = roadmap.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS event readiness outline source promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS event readiness outline source selected decision")
    _event_readiness_row(roadmap)
    firewall = roadmap.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS event readiness outline source allowed {key}")


def build_aas_event_readiness_observation_outline(
    *,
    artifact_dir: str | Path | None = None,
    source_roadmap: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative Event Readiness observation outline."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    roadmap = source_roadmap or load_aas_concept_gap_implementation_roadmap(
        artifact_dir=source_dir
    )
    _assert_source_roadmap(roadmap)
    row = _event_readiness_row(roadmap)

    outline = {
        "schema": AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SCHEMA,
        "observation_outline_id": AAS_EVENT_READINESS_OBSERVATION_OUTLINE_ID,
        "observation_outline_status": AAS_EVENT_READINESS_OBSERVATION_OUTLINE_STATUS,
        "source_roadmap": {
            "file": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
            "schema": roadmap["schema"],
            "roadmap_id": roadmap["roadmap_id"],
            "safe_claim": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
            "digest_sha256": _stable_digest(roadmap),
            "consumed_row_family": "event_readiness",
            "consumed_row_rank": row["planning_sequence_rank"],
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service Event Readiness planning",
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
        "event_readiness_observation_outline": {
            "aas_family": "event_readiness",
            "allowed_use": "internal_admin_observed_pre_event_blocker_outline_no_permit_security_or_outcome_claim",
            "source_backed_current_state": row["source_backed_current_state"],
            "implementation_concept_expansion": row["implementation_concept_expansion"],
            "roadmap_next_planning_slice": row["roadmap_next_planning_slice"],
            "concept_mode": row["next_allowed_without_human_answer"],
            "observation_fields": list(OBSERVATION_FIELDS),
            "observation_boundaries": list(OBSERVATION_BOUNDARIES),
            "safe_internal_language": list(SAFE_LANGUAGE),
            "forbidden_language": list(FORBIDDEN_LANGUAGE),
            "next_gate_before_any_delivery_or_runtime_movement": "separate_explicit_operator_answer_receipt_then_event_readiness_customer_or_dispatch_gate",
            "still_blocked": True,
        },
        "sequence_rules": [
            "Treat this outline as an internal/admin concept observation only, never as approval or customer copy.",
            "Do not authorize event site access, permits, security posture, vendors, venue decisions, or crowd-control claims from this outline.",
            "Do not convert visible pre-event observations into capacity, attendance, safety, outcome, SLA, or dispatch readiness.",
            "Create a separate explicit answer receipt before any Event Readiness customer, worker, event, or dispatch gate.",
            "Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.",
        ],
        "claim_boundaries": {
            "safe_to_claim": [
                AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
                AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(EVENT_READINESS_OBSERVATION_BLOCKED_CLAIMS),
        },
        "observation_outline_digest_sha256": "",
    }
    outline["observation_outline_digest_sha256"] = _stable_digest(
        {k: v for k, v in outline.items() if k != "observation_outline_digest_sha256"}
    )
    _assert_observation_outline_conservative(outline, source_roadmap=roadmap)
    return outline


def write_aas_event_readiness_observation_outline(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Event Readiness observation outline."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    outline = build_aas_event_readiness_observation_outline(artifact_dir=base_dir)
    path = base_dir / AAS_EVENT_READINESS_OBSERVATION_OUTLINE_FILENAME
    path.write_text(json.dumps(outline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_event_readiness_observation_outline(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Event Readiness observation outline."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    outline = json.loads(
        (base_dir / AAS_EVENT_READINESS_OBSERVATION_OUTLINE_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_roadmap = load_aas_concept_gap_implementation_roadmap(artifact_dir=base_dir)
    _assert_observation_outline_conservative(outline, source_roadmap=source_roadmap)
    return outline


def _assert_observation_outline_conservative(
    outline: dict[str, Any], *, source_roadmap: dict[str, Any]
) -> None:
    _assert_source_roadmap(source_roadmap)
    if outline.get("schema") != AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SCHEMA:
        raise CityOpsContractError("AAS event readiness outline schema drift")
    if outline.get("observation_outline_id") != AAS_EVENT_READINESS_OBSERVATION_OUTLINE_ID:
        raise CityOpsContractError("AAS event readiness outline id drift")
    if outline.get("observation_outline_status") != AAS_EVENT_READINESS_OBSERVATION_OUTLINE_STATUS:
        raise CityOpsContractError("AAS event readiness outline status drift")
    source = outline.get("source_roadmap", {})
    if source.get("digest_sha256") != _stable_digest(source_roadmap):
        raise CityOpsContractError("AAS event readiness outline source digest drift")
    if source.get("consumed_row_family") != "event_readiness" or source.get(
        "consumed_row_rank"
    ) != 5:
        raise CityOpsContractError("AAS event readiness outline consumed wrong row")

    state = outline.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(
                f"AAS event readiness outline operator state promoted {key}"
            )
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS event readiness outline selected future decision")

    for key, expected in FALSE_FLAGS.items():
        if outline.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS event readiness outline readiness promoted {key}")

    fixture = outline.get("event_readiness_observation_outline", {})
    if fixture.get("aas_family") != "event_readiness":
        raise CityOpsContractError("AAS event readiness outline family drift")
    if fixture.get("allowed_use") != "internal_admin_observed_pre_event_blocker_outline_no_permit_security_or_outcome_claim":
        raise CityOpsContractError("AAS event readiness outline use drift")
    if fixture.get("concept_mode") != "concept_outline_only":
        raise CityOpsContractError("AAS event readiness outline concept mode drift")
    if fixture.get("still_blocked") is not True:
        raise CityOpsContractError("AAS event readiness outline unblocked")
    if fixture.get("next_gate_before_any_delivery_or_runtime_movement") != (
        "separate_explicit_operator_answer_receipt_then_event_readiness_customer_or_dispatch_gate"
    ):
        raise CityOpsContractError("AAS event readiness outline next gate drift")
    if set(OBSERVATION_FIELDS) - set(fixture.get("observation_fields", [])):
        raise CityOpsContractError("AAS event readiness outline missing observation fields")
    if set(OBSERVATION_BOUNDARIES) - set(fixture.get("observation_boundaries", [])):
        raise CityOpsContractError("AAS event readiness outline missing observation boundaries")
    if set(FORBIDDEN_LANGUAGE) - set(fixture.get("forbidden_language", [])):
        raise CityOpsContractError("AAS event readiness outline missing forbidden language")
    for forbidden in ["permit approved", "security cleared", "event guaranteed", "dispatch ready"]:
        if forbidden in set(fixture.get("safe_internal_language", [])):
            raise CityOpsContractError("AAS event readiness outline safe language promoted")

    safe = set(outline.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(outline.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS event readiness outline safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS event readiness outline forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(EVENT_READINESS_OBSERVATION_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS event readiness outline missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"AAS event readiness outline claim overlap: {sorted(overlap)}"
        )

    firewall = outline.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS event readiness outline allowed {key}")
