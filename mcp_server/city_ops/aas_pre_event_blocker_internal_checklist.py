"""Internal/admin Pre-Event Blocker Check checklist menu.

This slice consumes the Event Readiness observation outline and turns it into a
held checklist grammar for future internal/admin review. It is not an operator
answer, approval record, answer receipt, customer/worker/public copy, event site
access authorization, permit/security/vendor/venue decision, crowd-safety claim,
catalog entry, dispatch route, runtime mutation, reputation event, or payment /
production change.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_event_readiness_observation_outline import (
    AAS_EVENT_READINESS_OBSERVATION_OUTLINE_FILENAME,
    AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM,
    AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SCHEMA,
    AAS_EVENT_READINESS_OBSERVATION_OUTLINE_STATUS,
    EVENT_READINESS_OBSERVATION_BLOCKED_CLAIMS,
    load_aas_event_readiness_observation_outline,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SCHEMA = (
    "city_ops.aas_pre_event_blocker_internal_checklist.v1"
)
AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_FILENAME = (
    "aas_pre_event_blocker_internal_checklist.json"
)
AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SAFE_CLAIM = (
    "internal_admin_aas_pre_event_blocker_internal_checklist_landed"
)
AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_ID = (
    "execution_market.aas.pre_event_blocker_internal_checklist.2026_06_14_0200"
)
AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_STATUS = (
    "internal_admin_checklist_no_answer_no_approval_no_event_access_no_permit_security_or_dispatch"
)

FALSE_FLAGS = {
    "checklist_records_operator_answer": False,
    "checklist_records_operator_approval": False,
    "checklist_creates_answer_receipt": False,
    "checklist_selects_event_type_or_future_answer": False,
    "checklist_approves_product_exposure": False,
    "checklist_creates_customer_public_or_worker_copy": False,
    "checklist_authorizes_event_site_access_or_recipient": False,
    "checklist_authorizes_permit_security_vendor_venue_or_crowd_control_decision": False,
    "checklist_certifies_capacity_safety_attendance_outcome_or_sla": False,
    "checklist_creates_catalog_pricing_quote_route_queue_or_dispatch": False,
    "checklist_creates_worker_instruction": False,
    "checklist_emits_reputation_or_worker_skill_dna": False,
    "checklist_reverifies_payment_or_production": False,
    "checklist_mutates_runtime_acontext_or_irc_session_manager": False,
    "checklist_releases_exact_gps_raw_metadata_private_context_or_pii": False,
    "checklist_grants_municipal_permit_legal_or_crowd_control_authority": False,
    "checklist_publishes_worker_copyable_doctrine": False,
    "checklist_integrates_or_expands_stopped_projects": False,
}

CHECKLIST_ROWS = [
    {
        "check_code": "visible_setup_presence_state",
        "allowed_check_values": [
            "setup_presence_visible",
            "setup_absent_from_allowed_view",
            "setup_partial_or_ambiguous",
            "not_observable_or_unknown",
        ],
        "safe_internal_read": "records only whether visible pre-event setup appears present from an allowed review context",
        "forbidden_promotion": "does_not_certify_operational_readiness_capacity_safety_attendance_or_event_outcome",
        "missing_truth_family": "authority_truth",
    },
    {
        "check_code": "wayfinding_and_staging_state",
        "allowed_check_values": [
            "wayfinding_or_staging_visible",
            "wayfinding_or_staging_absent_from_allowed_view",
            "wayfinding_or_staging_inconsistent_or_unclear",
            "not_observable_or_unknown",
        ],
        "safe_internal_read": "records visible wayfinding or staging markers without deciding whether they are sufficient",
        "forbidden_promotion": "does_not_confirm_permit_compliance_crowd_flow_accessibility_or_event_readiness",
        "missing_truth_family": "authority_truth",
    },
    {
        "check_code": "apparent_access_or_obstruction_state",
        "allowed_check_values": [
            "no_visible_obstruction_from_allowed_view",
            "apparent_obstruction_visible",
            "access_path_not_visible_or_not_checked",
            "not_observable_or_unknown",
        ],
        "safe_internal_read": "records only visible obstruction signals without access or crowd-control authority",
        "forbidden_promotion": "does_not_authorize_entry_removal_route_change_security_action_or_safety_clearance",
        "missing_truth_family": "authority_truth",
    },
    {
        "check_code": "visible_vendor_or_equipment_state",
        "allowed_check_values": [
            "vendor_or_equipment_presence_visible",
            "vendor_or_equipment_absent_from_allowed_view",
            "vendor_or_equipment_presence_unclear",
            "not_observable_or_unknown",
        ],
        "safe_internal_read": "records visible vendor or equipment presence without performance or commitment claims",
        "forbidden_promotion": "does_not_confirm_vendor_commitment_equipment_functionality_service_level_or_delivery_outcome",
        "missing_truth_family": "surface_truth",
    },
    {
        "check_code": "time_window_warning_state",
        "allowed_check_values": [
            "inside_named_observation_window",
            "outside_or_after_named_observation_window",
            "window_unverified_or_ambiguous",
            "not_applicable_or_unknown",
        ],
        "safe_internal_read": "keeps any pre-event blocker observation tied to a bounded time window",
        "forbidden_promotion": "does_not_create_monitoring_sla_real_time_status_or_event_day_guarantee",
        "missing_truth_family": "runtime_truth",
    },
    {
        "check_code": "redacted_reference_state",
        "allowed_check_values": [
            "redacted_reference_available",
            "redaction_required_before_reference",
            "withheld_private_context_or_raw_metadata",
            "not_applicable_or_unknown",
        ],
        "safe_internal_read": "tracks whether a redacted internal reference can support the blocker row",
        "forbidden_promotion": "does_not_release_exact_location_raw_metadata_private_context_contact_data_or_pii",
        "missing_truth_family": "location_privacy_truth",
    },
    {
        "check_code": "unresolved_not_checked_state",
        "allowed_check_values": [
            "explicitly_not_checked",
            "blocked_by_visibility_or_scope_limit",
            "contradictory_or_inconclusive_needs_review",
            "clear_within_allowed_view",
        ],
        "safe_internal_read": "keeps not-checked and inconclusive facts attached to any blocker summary",
        "forbidden_promotion": "does_not_convert_omitted_ambiguous_or_out_of_scope_facts_into_customer_ready_claims",
        "missing_truth_family": "operator_truth",
    },
]

REQUIRED_CHECK_CODES = [row["check_code"] for row in CHECKLIST_ROWS]

PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_BLOCKED_CLAIMS = [
    *EVENT_READINESS_OBSERVATION_BLOCKED_CLAIMS,
    "pre_event_blocker_checklist_records_operator_answer",
    "pre_event_blocker_checklist_records_operator_approval",
    "pre_event_blocker_checklist_creates_answer_receipt",
    "pre_event_blocker_checklist_selects_event_type_future_answer_or_collection_method",
    "pre_event_blocker_checklist_treats_check_option_as_approval",
    "pre_event_blocker_checklist_approves_product_exposure",
    "pre_event_blocker_checklist_creates_customer_public_or_worker_copy",
    "pre_event_blocker_checklist_authorizes_event_site_access_recipient_or_customer_use",
    "pre_event_blocker_checklist_authorizes_permit_security_vendor_venue_or_crowd_control_decision",
    "pre_event_blocker_checklist_certifies_capacity_safety_attendance_outcome_or_sla",
    "pre_event_blocker_checklist_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "pre_event_blocker_checklist_creates_worker_instruction",
    "pre_event_blocker_checklist_emits_erc8004_reputation_or_worker_skill_dna",
    "pre_event_blocker_checklist_reverifies_payment_or_production",
    "pre_event_blocker_checklist_mutates_runtime_acontext_or_irc_session_manager",
    "pre_event_blocker_checklist_releases_exact_gps_raw_metadata_private_context_or_pii",
    "pre_event_blocker_checklist_grants_municipal_permit_legal_or_crowd_control_authority",
    "pre_event_blocker_checklist_publishes_worker_copyable_doctrine",
    "pre_event_blocker_checklist_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "event_type_selected",
    "collection_authorized",
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
    "raw_metadata_release_ready",
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


def _assert_source_outline(outline: dict[str, Any]) -> None:
    if outline.get("schema") != AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SCHEMA:
        raise CityOpsContractError("AAS pre-event blocker checklist source schema drift")
    if outline.get("observation_outline_status") != AAS_EVENT_READINESS_OBSERVATION_OUTLINE_STATUS:
        raise CityOpsContractError("AAS pre-event blocker checklist source status drift")
    safe = set(outline.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS pre-event blocker checklist source safe claim missing")
    blocked = set(outline.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(EVENT_READINESS_OBSERVATION_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS pre-event blocker checklist source missing blocked claims: {sorted(missing)}"
        )
    state = outline.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS pre-event blocker checklist source promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS pre-event blocker checklist source selected decision")
    for key, value in outline.get("readiness", {}).items():
        if value is not False:
            raise CityOpsContractError(f"AAS pre-event blocker checklist source readiness promoted {key}")
    body = outline.get("event_readiness_observation_outline", {})
    if body.get("still_blocked") is not True:
        raise CityOpsContractError("AAS pre-event blocker checklist source unblocked")
    if body.get("concept_mode") != "concept_outline_only":
        raise CityOpsContractError("AAS pre-event blocker checklist source concept mode drift")
    if body.get("aas_family") != "event_readiness":
        raise CityOpsContractError("AAS pre-event blocker checklist source family drift")
    firewall = outline.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS pre-event blocker checklist source allowed {key}")


def build_aas_pre_event_blocker_internal_checklist(
    *,
    artifact_dir: str | Path | None = None,
    source_outline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative Pre-Event Blocker Check internal checklist."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    outline = source_outline or load_aas_event_readiness_observation_outline(
        artifact_dir=source_dir
    )
    _assert_source_outline(outline)

    checklist = {
        "schema": AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SCHEMA,
        "checklist_id": AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_ID,
        "checklist_status": AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_STATUS,
        "source_outline": {
            "file": AAS_EVENT_READINESS_OBSERVATION_OUTLINE_FILENAME,
            "schema": outline["schema"],
            "observation_outline_id": outline["observation_outline_id"],
            "safe_claim": AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM,
            "digest_sha256": _stable_digest(outline),
            "consumed_family": "event_readiness",
            "canonical_family": "Pre-Event Blocker Check",
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service Pre-Event Blocker Check planning",
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
            "event_type_selected": False,
            "collection_method_authorized": False,
            "selected_decision": None,
            "recommended_no_human_posture": "checklist_only",
        },
        "readiness": dict(FALSE_FLAGS),
        "pre_event_blocker_internal_checklist": {
            "canonical_family": "Pre-Event Blocker Check",
            "legacy_source_family": "event_readiness",
            "allowed_use": "internal_admin_checklist_only_no_event_type_no_site_access_no_customer_copy",
            "checklist_mode": "checklist_only",
            "checklist_rows": list(CHECKLIST_ROWS),
            "required_check_codes": list(REQUIRED_CHECK_CODES),
            "row_contract": {
                "must_include_check_code": True,
                "must_include_allowed_check_values": True,
                "must_include_safe_internal_read": True,
                "must_include_forbidden_promotion": True,
                "must_include_missing_truth_family": True,
            },
            "allowed_truth_families": [
                "operator_truth",
                "surface_truth",
                "runtime_truth",
                "location_privacy_truth",
                "authority_truth",
            ],
            "next_gate_before_any_delivery_or_runtime_movement": "separate_event_type_observation_window_and_operator_answer_receipt",
            "still_blocked": True,
        },
        "sequence_rules": [
            "Treat the checklist as internal/admin grammar only; never as approval, customer copy, or worker instruction.",
            "Do not select an event type, site, collection method, route, queue, dispatch path, or recipient from this checklist.",
            "Do not convert visible blocker rows into permit, security, crowd-control, vendor, capacity, safety, SLA, or outcome claims.",
            "Do not expose exact location, raw metadata, private context, PII, contact data, or unredacted references from this checklist.",
            "Create a separate explicit operator answer receipt before any Pre-Event Blocker Check customer, worker, field, catalog, or runtime gate.",
            "Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.",
        ],
        "claim_boundaries": {
            "safe_to_claim": [
                AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM,
                AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_BLOCKED_CLAIMS),
        },
        "checklist_digest_sha256": "",
    }
    checklist["checklist_digest_sha256"] = _stable_digest(
        {k: v for k, v in checklist.items() if k != "checklist_digest_sha256"}
    )
    _assert_internal_checklist_conservative(checklist, source_outline=outline)
    return checklist


def write_aas_pre_event_blocker_internal_checklist(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Pre-Event Blocker Check internal checklist."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    checklist = build_aas_pre_event_blocker_internal_checklist(artifact_dir=base_dir)
    path = base_dir / AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_FILENAME
    path.write_text(json.dumps(checklist, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_pre_event_blocker_internal_checklist(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Pre-Event Blocker Check checklist."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    checklist = json.loads(
        (base_dir / AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_outline = load_aas_event_readiness_observation_outline(artifact_dir=base_dir)
    _assert_internal_checklist_conservative(checklist, source_outline=source_outline)
    return checklist


def _assert_internal_checklist_conservative(
    checklist: dict[str, Any], *, source_outline: dict[str, Any]
) -> None:
    _assert_source_outline(source_outline)
    if checklist.get("schema") != AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SCHEMA:
        raise CityOpsContractError("AAS pre-event blocker checklist schema drift")
    if checklist.get("checklist_id") != AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_ID:
        raise CityOpsContractError("AAS pre-event blocker checklist id drift")
    if checklist.get("checklist_status") != AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_STATUS:
        raise CityOpsContractError("AAS pre-event blocker checklist status drift")
    source = checklist.get("source_outline", {})
    if source.get("digest_sha256") != _stable_digest(source_outline):
        raise CityOpsContractError("AAS pre-event blocker checklist source digest drift")
    if source.get("canonical_family") != "Pre-Event Blocker Check":
        raise CityOpsContractError("AAS pre-event blocker checklist canonical family drift")
    if source.get("consumed_family") != "event_readiness":
        raise CityOpsContractError("AAS pre-event blocker checklist consumed wrong family")

    state = checklist.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
        "event_type_selected",
        "collection_method_authorized",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS pre-event blocker checklist promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS pre-event blocker checklist selected future decision")

    for key, expected in FALSE_FLAGS.items():
        if checklist.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS pre-event blocker checklist readiness promoted {key}")

    body = checklist.get("pre_event_blocker_internal_checklist", {})
    if body.get("canonical_family") != "Pre-Event Blocker Check":
        raise CityOpsContractError("AAS pre-event blocker checklist family drift")
    if body.get("legacy_source_family") != "event_readiness":
        raise CityOpsContractError("AAS pre-event blocker checklist legacy family drift")
    if body.get("allowed_use") != "internal_admin_checklist_only_no_event_type_no_site_access_no_customer_copy":
        raise CityOpsContractError("AAS pre-event blocker checklist use drift")
    if body.get("checklist_mode") != "checklist_only":
        raise CityOpsContractError("AAS pre-event blocker checklist mode drift")
    if body.get("still_blocked") is not True:
        raise CityOpsContractError("AAS pre-event blocker checklist unblocked")
    if body.get("next_gate_before_any_delivery_or_runtime_movement") != (
        "separate_event_type_observation_window_and_operator_answer_receipt"
    ):
        raise CityOpsContractError("AAS pre-event blocker checklist next gate drift")

    rows = body.get("checklist_rows", [])
    row_codes = [row.get("check_code") for row in rows]
    if row_codes != REQUIRED_CHECK_CODES:
        raise CityOpsContractError("AAS pre-event blocker checklist code drift")
    if body.get("required_check_codes") != REQUIRED_CHECK_CODES:
        raise CityOpsContractError("AAS pre-event blocker checklist required codes drift")
    allowed_truth_families = set(body.get("allowed_truth_families", []))
    for row in rows:
        for key in [
            "check_code",
            "allowed_check_values",
            "safe_internal_read",
            "forbidden_promotion",
            "missing_truth_family",
        ]:
            if key not in row:
                raise CityOpsContractError(f"AAS pre-event blocker checklist row missing {key}")
        if not row.get("allowed_check_values"):
            raise CityOpsContractError("AAS pre-event blocker checklist row empty values")
        if row.get("missing_truth_family") not in allowed_truth_families:
            raise CityOpsContractError("AAS pre-event blocker checklist wrong truth family")
        forbidden = row.get("forbidden_promotion", "")
        for required_fragment in ["does_not", "or"]:
            if required_fragment not in forbidden:
                raise CityOpsContractError("AAS pre-event blocker checklist weak forbidden promotion")

    safe = set(checklist.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(checklist.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS pre-event blocker checklist safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS pre-event blocker checklist forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS pre-event blocker checklist missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"AAS pre-event blocker checklist claim overlap: {sorted(overlap)}"
        )

    firewall = checklist.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS pre-event blocker checklist allowed {key}")
