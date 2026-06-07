"""Internal/admin Incident Verification observation/uncertainty maintenance.

This slice consumes the AAS concept-gap implementation roadmap and expands only
its rank-6 Incident Verification maintenance action. It is deliberately not an
operator answer, approval record, answer receipt, customer/worker/public copy,
emergency response claim, official report, fault/liability assignment, repair
instruction, dispatch surface, or runtime movement.
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

AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_SCHEMA = (
    "city_ops.aas_incident_verification_observation_uncertainty_maintenance.v1"
)
AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_FILENAME = (
    "aas_incident_verification_observation_uncertainty_maintenance.json"
)
AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_SAFE_CLAIM = (
    "internal_admin_aas_incident_verification_observation_uncertainty_maintenance_landed"
)
AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_ID = (
    "execution_market.aas.incident_verification_observation_uncertainty_maintenance.2026_06_06_2200"
)
AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_STATUS = (
    "internal_admin_maintenance_no_answer_no_approval_no_emergency_official_fault_or_repair_claim"
)

FALSE_FLAGS = {
    "maintenance_records_operator_answer": False,
    "maintenance_records_operator_approval": False,
    "maintenance_creates_answer_receipt": False,
    "maintenance_selects_future_answer": False,
    "maintenance_approves_product_exposure": False,
    "maintenance_creates_customer_public_or_worker_copy": False,
    "maintenance_authorizes_incident_site_access_or_recipient": False,
    "maintenance_authorizes_emergency_response_or_safety_decision": False,
    "maintenance_creates_official_report_fault_liability_or_insurance_claim": False,
    "maintenance_authorizes_repair_remediation_or_completion_claim": False,
    "maintenance_creates_public_catalog_pricing_quote_or_route": False,
    "maintenance_launches_queue_dispatch_or_worker_instruction": False,
    "maintenance_emits_reputation_or_worker_skill_dna": False,
    "maintenance_reverifies_payment_or_production": False,
    "maintenance_mutates_runtime_acontext_or_irc": False,
    "maintenance_exposes_exact_gps_raw_metadata_private_context_or_pii": False,
    "maintenance_grants_emergency_legal_insurance_sla_or_fault_authority": False,
    "maintenance_publishes_worker_copyable_doctrine": False,
    "maintenance_integrates_or_expands_stopped_projects": False,
}

OBSERVATION_UNCERTAINTY_FIELDS = [
    "incident_identifier_placeholder_without_private_location_or_parties",
    "observation_window_placeholder_without_private_context",
    "visible_condition_or_state_observed_without_cause_assignment",
    "source_type_placeholder_after_redaction_review",
    "uncertainty_or_ambiguity_statement_required",
    "non_authority_disclaimer_for_emergency_safety_fault_and_liability",
    "photo_screenshot_or_text_reference_placeholder_after_redaction_review",
    "unknowns_and_unresolved_observations",
]

MAINTENANCE_BOUNDARIES = [
    "record_only_observation_and_uncertainty_language_not_incident_authority",
    "separate_visible_state_from_cause_fault_liability_and_official_reporting",
    "do_not_infer_emergency_response_safety_repair_or_insurance_decision",
    "do_not_publish_exact_location_private_context_raw_metadata_or_pii",
    "customer_or_worker_copy_requires_separate_explicit_answer_receipt",
]

SAFE_LANGUAGE = [
    "incident observation uncertainty language maintenance only",
    "emergency official-report fault and repair claims blocked",
    "visible condition does not assign cause or liability",
    "uncertainty statement required before any future review",
    "future answer receipt required before incident delivery or customer use",
]

FORBIDDEN_LANGUAGE = [
    "emergency verified",
    "official report complete",
    "fault assigned",
    "liability confirmed",
    "repair required",
    "safe condition certified",
    "insurance ready",
    "dispatch ready",
]

INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_BLOCKED_CLAIMS = [
    *ROADMAP_BLOCKED_CLAIMS,
    "incident_verification_observation_uncertainty_maintenance_records_operator_answer",
    "incident_verification_observation_uncertainty_maintenance_records_operator_approval",
    "incident_verification_observation_uncertainty_maintenance_creates_answer_receipt",
    "incident_verification_observation_uncertainty_maintenance_selects_future_answer",
    "incident_verification_observation_uncertainty_maintenance_treats_maintenance_as_approval",
    "incident_verification_observation_uncertainty_maintenance_approves_product_exposure",
    "incident_verification_observation_uncertainty_maintenance_creates_customer_public_or_worker_copy",
    "incident_verification_observation_uncertainty_maintenance_authorizes_incident_site_access_recipient_or_customer_use",
    "incident_verification_observation_uncertainty_maintenance_authorizes_emergency_response_or_safety_decision",
    "incident_verification_observation_uncertainty_maintenance_creates_official_report_fault_liability_or_insurance_claim",
    "incident_verification_observation_uncertainty_maintenance_authorizes_repair_remediation_or_completion_claim",
    "incident_verification_observation_uncertainty_maintenance_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "incident_verification_observation_uncertainty_maintenance_creates_worker_instruction",
    "incident_verification_observation_uncertainty_maintenance_emits_erc8004_reputation_or_worker_skill_dna",
    "incident_verification_observation_uncertainty_maintenance_reverifies_payment_or_production",
    "incident_verification_observation_uncertainty_maintenance_mutates_runtime_acontext_or_irc_session_manager",
    "incident_verification_observation_uncertainty_maintenance_releases_exact_gps_raw_metadata_private_context_or_pii",
    "incident_verification_observation_uncertainty_maintenance_grants_emergency_legal_insurance_sla_or_fault_authority",
    "incident_verification_observation_uncertainty_maintenance_publishes_worker_copyable_doctrine",
    "incident_verification_observation_uncertainty_maintenance_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "incident_verification_approved",
    "incident_verification_customer_ready",
    "incident_site_access_authorized",
    "emergency_response_ready",
    "safety_certification_ready",
    "official_incident_report_ready",
    "fault_or_liability_assignment_ready",
    "insurance_adjustment_ready",
    "repair_authorized",
    "repair_completion_ready",
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


def _incident_verification_row(roadmap: dict[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in roadmap.get("roadmap_rows", [])
        if row.get("aas_family") == "incident_verification"
    ]
    if len(rows) != 1:
        raise CityOpsContractError("AAS incident verification maintenance source row missing")
    row = rows[0]
    if row.get("planning_sequence_rank") != 6:
        raise CityOpsContractError("AAS incident verification maintenance source rank drift")
    if row.get("roadmap_next_planning_slice") != "observation_uncertainty_language_maintenance_only":
        raise CityOpsContractError("AAS incident verification maintenance source action drift")
    if row.get("still_blocked") is not True:
        raise CityOpsContractError("AAS incident verification maintenance source row unblocked")
    if row.get("next_allowed_without_human_answer") != "maintenance_only_no_approval_record":
        raise CityOpsContractError("AAS incident verification maintenance source mode drift")
    return row


def _assert_source_roadmap(roadmap: dict[str, Any]) -> None:
    if roadmap.get("schema") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA:
        raise CityOpsContractError("AAS incident verification maintenance source schema drift")
    if roadmap.get("roadmap_status") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS:
        raise CityOpsContractError("AAS incident verification maintenance source status drift")
    safe = set(roadmap.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS incident verification maintenance source safe claim missing")
    blocked = set(roadmap.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(ROADMAP_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS incident verification maintenance source missing blocked claims: {sorted(missing)}"
        )
    state = roadmap.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS incident verification maintenance source promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS incident verification maintenance source selected decision")
    _incident_verification_row(roadmap)
    firewall = roadmap.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS incident verification maintenance source allowed {key}")


def build_aas_incident_verification_observation_uncertainty_maintenance(
    *,
    artifact_dir: str | Path | None = None,
    source_roadmap: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build conservative Incident Verification observation/uncertainty maintenance."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    roadmap = source_roadmap or load_aas_concept_gap_implementation_roadmap(
        artifact_dir=source_dir
    )
    _assert_source_roadmap(roadmap)
    row = _incident_verification_row(roadmap)

    maintenance = {
        "schema": AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_SCHEMA,
        "maintenance_id": AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_ID,
        "maintenance_status": AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_STATUS,
        "source_roadmap": {
            "file": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
            "schema": roadmap["schema"],
            "roadmap_id": roadmap["roadmap_id"],
            "safe_claim": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
            "digest_sha256": _stable_digest(roadmap),
            "consumed_row_family": "incident_verification",
            "consumed_row_rank": row["planning_sequence_rank"],
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service Incident Verification planning",
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
            "recommended_no_human_posture": "maintenance_only_no_approval_record",
        },
        "readiness": dict(FALSE_FLAGS),
        "incident_verification_observation_uncertainty_maintenance": {
            "aas_family": "incident_verification",
            "allowed_use": "internal_admin_observation_uncertainty_language_maintenance_no_approval_record",
            "source_backed_current_state": row["source_backed_current_state"],
            "implementation_concept_expansion": row["implementation_concept_expansion"],
            "roadmap_next_planning_slice": row["roadmap_next_planning_slice"],
            "maintenance_mode": row["next_allowed_without_human_answer"],
            "observation_uncertainty_fields": list(OBSERVATION_UNCERTAINTY_FIELDS),
            "maintenance_boundaries": list(MAINTENANCE_BOUNDARIES),
            "safe_internal_language": list(SAFE_LANGUAGE),
            "forbidden_language": list(FORBIDDEN_LANGUAGE),
            "next_gate_before_any_delivery_or_runtime_movement": "separate_explicit_operator_answer_receipt_then_incident_verification_customer_or_dispatch_gate",
            "still_blocked": True,
        },
        "sequence_rules": [
            "Treat this maintenance artifact as internal/admin language hygiene only, never as approval or customer copy.",
            "Do not authorize incident site access, emergency response, safety decisions, official reports, repair, insurance, fault, or liability claims from this maintenance artifact.",
            "Do not convert visible incident observations into cause assignment, remediation instruction, SLA, or dispatch readiness.",
            "Create a separate explicit answer receipt before any Incident Verification customer, worker, incident, or dispatch gate.",
            "Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.",
        ],
        "claim_boundaries": {
            "safe_to_claim": [
                AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
                AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(
                INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_BLOCKED_CLAIMS
            ),
        },
        "maintenance_digest_sha256": "",
    }
    maintenance["maintenance_digest_sha256"] = _stable_digest(
        {k: v for k, v in maintenance.items() if k != "maintenance_digest_sha256"}
    )
    _assert_maintenance_conservative(maintenance, source_roadmap=roadmap)
    return maintenance


def write_aas_incident_verification_observation_uncertainty_maintenance(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Incident Verification observation/uncertainty maintenance artifact."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    maintenance = build_aas_incident_verification_observation_uncertainty_maintenance(
        artifact_dir=base_dir
    )
    path = base_dir / AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_FILENAME
    path.write_text(json.dumps(maintenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_incident_verification_observation_uncertainty_maintenance(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Incident Verification maintenance artifact."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = base_dir / AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_FILENAME
    maintenance = json.loads(path.read_text(encoding="utf-8"))
    source_roadmap = load_aas_concept_gap_implementation_roadmap(artifact_dir=base_dir)
    _assert_maintenance_conservative(maintenance, source_roadmap=source_roadmap)
    return maintenance


def _assert_maintenance_conservative(
    maintenance: dict[str, Any], *, source_roadmap: dict[str, Any]
) -> None:
    if maintenance.get("schema") != AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_SCHEMA:
        raise CityOpsContractError("AAS incident verification maintenance schema drift")
    if maintenance.get("maintenance_status") != AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_STATUS:
        raise CityOpsContractError("AAS incident verification maintenance status drift")

    _assert_source_roadmap(source_roadmap)
    source = maintenance.get("source_roadmap", {})
    if source.get("digest_sha256") != _stable_digest(source_roadmap):
        raise CityOpsContractError("AAS incident verification maintenance source digest drift")
    if source.get("consumed_row_family") != "incident_verification" or source.get("consumed_row_rank") != 6:
        raise CityOpsContractError("AAS incident verification maintenance consumed row drift")

    state = maintenance.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS incident verification maintenance promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS incident verification maintenance selected decision")

    for key, expected in FALSE_FLAGS.items():
        if maintenance.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS incident verification maintenance promoted {key}")

    fixture = maintenance.get("incident_verification_observation_uncertainty_maintenance", {})
    if fixture.get("aas_family") != "incident_verification":
        raise CityOpsContractError("AAS incident verification maintenance family drift")
    if fixture.get("maintenance_mode") != "maintenance_only_no_approval_record":
        raise CityOpsContractError("AAS incident verification maintenance mode drift")
    if fixture.get("still_blocked") is not True:
        raise CityOpsContractError("AAS incident verification maintenance unblocked")

    missing_fields = set(OBSERVATION_UNCERTAINTY_FIELDS) - set(
        fixture.get("observation_uncertainty_fields", [])
    )
    if missing_fields:
        raise CityOpsContractError(
            f"AAS incident verification maintenance missing observation uncertainty fields: {sorted(missing_fields)}"
        )
    missing_boundaries = set(MAINTENANCE_BOUNDARIES) - set(
        fixture.get("maintenance_boundaries", [])
    )
    if missing_boundaries:
        raise CityOpsContractError(
            f"AAS incident verification maintenance missing boundaries: {sorted(missing_boundaries)}"
        )
    if set(FORBIDDEN_LANGUAGE) - set(fixture.get("forbidden_language", [])):
        raise CityOpsContractError("AAS incident verification maintenance forbidden language drift")
    forbidden_safe_language = set(FORBIDDEN_LANGUAGE) & set(
        fixture.get("safe_internal_language", [])
    )
    if forbidden_safe_language:
        raise CityOpsContractError(
            f"AAS incident verification maintenance unsafe safe-language terms: {sorted(forbidden_safe_language)}"
        )

    safe = set(maintenance.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(maintenance.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_MAINTENANCE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS incident verification maintenance safe claim missing")
    if safe & blocked:
        raise CityOpsContractError("AAS incident verification maintenance safe/blocked overlap")
    missing_blocked = set(INCIDENT_VERIFICATION_OBSERVATION_UNCERTAINTY_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS incident verification maintenance missing blocked claims: {sorted(missing_blocked)}"
        )
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS incident verification maintenance forbidden safe claims: {sorted(forbidden_safe)}"
        )

    firewall = maintenance.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS incident verification maintenance allowed {key}")

    expected_digest = _stable_digest(
        {k: v for k, v in maintenance.items() if k != "maintenance_digest_sha256"}
    )
    if maintenance.get("maintenance_digest_sha256") != expected_digest:
        raise CityOpsContractError("AAS incident verification maintenance digest drift")
