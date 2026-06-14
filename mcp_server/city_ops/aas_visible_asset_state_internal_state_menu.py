"""Internal/admin Visible Asset State Snapshot state menu.

This slice consumes the Field Asset Ops visible-state fixture outline and turns it
into a held state-menu grammar for future internal/admin review. It is not an
operator answer, approval record, answer receipt, customer/worker/public copy,
field visit authorization, inspection result, repair instruction, SLA/warranty/
safety claim, catalog entry, dispatch route, runtime mutation, reputation event,
or payment/production change.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_field_asset_visible_state_fixture_outline import (
    AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_FILENAME,
    AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM,
    AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SCHEMA,
    AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_STATUS,
    FIELD_ASSET_VISIBLE_STATE_BLOCKED_CLAIMS,
    load_aas_field_asset_visible_state_fixture_outline,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SCHEMA = (
    "city_ops.aas_visible_asset_state_internal_state_menu.v1"
)
AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_FILENAME = (
    "aas_visible_asset_state_internal_state_menu.json"
)
AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SAFE_CLAIM = (
    "internal_admin_aas_visible_asset_state_internal_state_menu_landed"
)
AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_ID = (
    "execution_market.aas.visible_asset_state_internal_state_menu.2026_06_14_0100"
)
AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_STATUS = (
    "internal_admin_state_menu_no_answer_no_approval_no_field_visit_no_repair_sla_or_customer_copy"
)

FALSE_FLAGS = {
    "menu_records_operator_answer": False,
    "menu_records_operator_approval": False,
    "menu_creates_answer_receipt": False,
    "menu_selects_asset_class_or_future_answer": False,
    "menu_approves_product_exposure": False,
    "menu_creates_customer_public_or_worker_copy": False,
    "menu_authorizes_field_visit_access_or_recipient": False,
    "menu_authorizes_inspection_repair_remediation_or_maintenance": False,
    "menu_certifies_asset_functionality_safety_warranty_or_sla": False,
    "menu_creates_catalog_pricing_quote_route_queue_or_dispatch": False,
    "menu_creates_worker_instruction": False,
    "menu_emits_reputation_or_worker_skill_dna": False,
    "menu_reverifies_payment_or_production": False,
    "menu_mutates_runtime_acontext_or_irc_session_manager": False,
    "menu_releases_exact_gps_raw_metadata_private_context_or_pii": False,
    "menu_grants_property_access_appraisal_or_maintenance_authority": False,
    "menu_publishes_worker_copyable_doctrine": False,
    "menu_integrates_or_expands_stopped_projects": False,
}

STATE_MENU_ROWS = [
    {
        "state_code": "visible_presence_state",
        "allowed_observation_values": [
            "present_observed",
            "absent_not_seen_from_allowed_view",
            "partially_visible",
            "not_observable_or_unknown",
        ],
        "safe_internal_read": "records whether the asset is visibly present from an allowed review context",
        "forbidden_promotion": "does_not_confirm_ownership_access_installation_functionality_or_availability",
        "missing_truth_family": "collection_truth",
    },
    {
        "state_code": "apparent_access_or_obstruction_state",
        "allowed_observation_values": [
            "no_obstruction_visible",
            "apparent_obstruction_visible",
            "access_path_not_visible",
            "not_observable_or_unknown",
        ],
        "safe_internal_read": "records only visible obstruction or non-obstruction without access authority",
        "forbidden_promotion": "does_not_authorize_entry_removal_repair_dispatch_or_safety_clearance",
        "missing_truth_family": "authority_truth",
    },
    {
        "state_code": "apparent_surface_condition_state",
        "allowed_observation_values": [
            "no_visible_surface_issue_from_allowed_view",
            "visible_wear_or_damage_marker",
            "surface_obscured_or_partially_visible",
            "not_observable_or_unknown",
        ],
        "safe_internal_read": "records visible surface markers only",
        "forbidden_promotion": "does_not_diagnose_root_cause_severity_repair_need_or_fault_liability",
        "missing_truth_family": "authority_truth",
    },
    {
        "state_code": "visible_indicator_state",
        "allowed_observation_values": [
            "indicator_visible_on_or_lit",
            "indicator_visible_off_or_unlit",
            "indicator_visible_but_unreadable",
            "no_indicator_visible",
            "not_observable_or_unknown",
        ],
        "safe_internal_read": "records visible indicator appearance without interpreting system function",
        "forbidden_promotion": "does_not_certify_functionality_safety_warranty_sla_or_operational_status",
        "missing_truth_family": "authority_truth",
    },
    {
        "state_code": "redacted_media_reference_state",
        "allowed_observation_values": [
            "redacted_reference_available",
            "redaction_required_before_reference",
            "withheld_private_context_or_raw_metadata",
            "not_applicable_or_unknown",
        ],
        "safe_internal_read": "tracks whether a redacted internal reference can support the visible-state row",
        "forbidden_promotion": "does_not_release_exact_location_raw_metadata_private_context_or_pii",
        "missing_truth_family": "location_privacy_truth",
    },
    {
        "state_code": "uncertainty_state",
        "allowed_observation_values": [
            "clear_within_allowed_view",
            "ambiguous_needs_review",
            "contradictory_sources_needs_review",
            "out_of_scope_not_checked",
        ],
        "safe_internal_read": "keeps uncertainty attached to the internal/admin row",
        "forbidden_promotion": "does_not_convert_uncertain_or_out_of_scope_data_into_customer_ready_fact",
        "missing_truth_family": "operator_truth",
    },
]

REQUIRED_STATE_CODES = [row["state_code"] for row in STATE_MENU_ROWS]

VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_BLOCKED_CLAIMS = [
    *FIELD_ASSET_VISIBLE_STATE_BLOCKED_CLAIMS,
    "visible_asset_state_menu_records_operator_answer",
    "visible_asset_state_menu_records_operator_approval",
    "visible_asset_state_menu_creates_answer_receipt",
    "visible_asset_state_menu_selects_asset_class_future_answer_or_collection_method",
    "visible_asset_state_menu_treats_state_option_as_approval",
    "visible_asset_state_menu_approves_product_exposure",
    "visible_asset_state_menu_creates_customer_public_or_worker_copy",
    "visible_asset_state_menu_authorizes_field_visit_access_recipient_or_customer_use",
    "visible_asset_state_menu_authorizes_inspection_repair_remediation_or_maintenance",
    "visible_asset_state_menu_certifies_functionality_safety_warranty_or_sla",
    "visible_asset_state_menu_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "visible_asset_state_menu_creates_worker_instruction",
    "visible_asset_state_menu_emits_erc8004_reputation_or_worker_skill_dna",
    "visible_asset_state_menu_reverifies_payment_or_production",
    "visible_asset_state_menu_mutates_runtime_acontext_or_irc_session_manager",
    "visible_asset_state_menu_releases_exact_gps_raw_metadata_private_context_or_pii",
    "visible_asset_state_menu_grants_property_access_appraisal_or_maintenance_authority",
    "visible_asset_state_menu_publishes_worker_copyable_doctrine",
    "visible_asset_state_menu_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "asset_class_selected",
    "collection_authorized",
    "field_visit_authorized",
    "inspection_authorized",
    "repair_authorized",
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
    if outline.get("schema") != AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SCHEMA:
        raise CityOpsContractError("AAS visible asset state menu source schema drift")
    if outline.get("fixture_outline_status") != AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_STATUS:
        raise CityOpsContractError("AAS visible asset state menu source status drift")
    safe = set(outline.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS visible asset state menu source safe claim missing")
    blocked = set(outline.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(FIELD_ASSET_VISIBLE_STATE_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS visible asset state menu source missing blocked claims: {sorted(missing)}"
        )
    state = outline.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS visible asset state menu source promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS visible asset state menu source selected decision")
    readiness = outline.get("readiness", {})
    for key, value in readiness.items():
        if value is not False:
            raise CityOpsContractError(f"AAS visible asset state menu source readiness promoted {key}")
    fixture = outline.get("field_asset_visible_state_fixture_outline", {})
    if fixture.get("still_blocked") is not True:
        raise CityOpsContractError("AAS visible asset state menu source unblocked")
    if fixture.get("concept_mode") != "concept_outline_only":
        raise CityOpsContractError("AAS visible asset state menu source concept mode drift")
    firewall = outline.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS visible asset state menu source allowed {key}")


def build_aas_visible_asset_state_internal_state_menu(
    *,
    artifact_dir: str | Path | None = None,
    source_outline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative Visible Asset State Snapshot internal state menu."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    outline = source_outline or load_aas_field_asset_visible_state_fixture_outline(
        artifact_dir=source_dir
    )
    _assert_source_outline(outline)

    menu = {
        "schema": AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SCHEMA,
        "state_menu_id": AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_ID,
        "state_menu_status": AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_STATUS,
        "source_outline": {
            "file": AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_FILENAME,
            "schema": outline["schema"],
            "fixture_outline_id": outline["fixture_outline_id"],
            "safe_claim": AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM,
            "digest_sha256": _stable_digest(outline),
            "consumed_family": "field_asset_ops",
            "canonical_family": "Visible Asset State Snapshot",
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service Visible Asset State Snapshot planning",
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
            "asset_class_selected": False,
            "collection_method_authorized": False,
            "selected_decision": None,
            "recommended_no_human_posture": "state_menu_only",
        },
        "readiness": dict(FALSE_FLAGS),
        "visible_asset_state_internal_state_menu": {
            "canonical_family": "Visible Asset State Snapshot",
            "legacy_source_family": "field_asset_ops",
            "allowed_use": "internal_admin_state_menu_only_no_asset_class_no_field_visit_no_customer_copy",
            "menu_mode": "state_menu_only",
            "state_menu_rows": list(STATE_MENU_ROWS),
            "required_state_codes": list(REQUIRED_STATE_CODES),
            "row_contract": {
                "must_include_state_code": True,
                "must_include_allowed_observation_values": True,
                "must_include_safe_internal_read": True,
                "must_include_forbidden_promotion": True,
                "must_include_missing_truth_family": True,
            },
            "allowed_truth_families": [
                "operator_truth",
                "collection_truth",
                "location_privacy_truth",
                "authority_truth",
            ],
            "next_gate_before_any_delivery_or_runtime_movement": "separate_asset_class_method_boundary_and_operator_answer_receipt",
            "still_blocked": True,
        },
        "sequence_rules": [
            "Treat the state menu as internal/admin grammar only; never as approval, customer copy, or worker instruction.",
            "Do not select an asset class, collection method, route, queue, dispatch path, or recipient from this menu.",
            "Do not convert visible-state rows into functionality, safety, warranty, SLA, repair, remediation, or access authority claims.",
            "Do not expose exact location, raw metadata, private context, PII, or unredacted media references from this menu.",
            "Create a separate explicit operator answer receipt before any Visible Asset State Snapshot customer, worker, field, catalog, or runtime gate.",
            "Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.",
        ],
        "claim_boundaries": {
            "safe_to_claim": [
                AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM,
                AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_BLOCKED_CLAIMS),
        },
        "state_menu_digest_sha256": "",
    }
    menu["state_menu_digest_sha256"] = _stable_digest(
        {k: v for k, v in menu.items() if k != "state_menu_digest_sha256"}
    )
    _assert_internal_state_menu_conservative(menu, source_outline=outline)
    return menu


def write_aas_visible_asset_state_internal_state_menu(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the Visible Asset State Snapshot internal state menu."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    menu = build_aas_visible_asset_state_internal_state_menu(artifact_dir=base_dir)
    path = base_dir / AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_FILENAME
    path.write_text(json.dumps(menu, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_visible_asset_state_internal_state_menu(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Visible Asset State Snapshot menu."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    menu = json.loads(
        (base_dir / AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_outline = load_aas_field_asset_visible_state_fixture_outline(artifact_dir=base_dir)
    _assert_internal_state_menu_conservative(menu, source_outline=source_outline)
    return menu


def _assert_internal_state_menu_conservative(
    menu: dict[str, Any], *, source_outline: dict[str, Any]
) -> None:
    _assert_source_outline(source_outline)
    if menu.get("schema") != AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SCHEMA:
        raise CityOpsContractError("AAS visible asset state menu schema drift")
    if menu.get("state_menu_id") != AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_ID:
        raise CityOpsContractError("AAS visible asset state menu id drift")
    if menu.get("state_menu_status") != AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_STATUS:
        raise CityOpsContractError("AAS visible asset state menu status drift")
    source = menu.get("source_outline", {})
    if source.get("digest_sha256") != _stable_digest(source_outline):
        raise CityOpsContractError("AAS visible asset state menu source digest drift")
    if source.get("canonical_family") != "Visible Asset State Snapshot":
        raise CityOpsContractError("AAS visible asset state menu canonical family drift")
    if source.get("consumed_family") != "field_asset_ops":
        raise CityOpsContractError("AAS visible asset state menu consumed wrong family")

    state = menu.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
        "asset_class_selected",
        "collection_method_authorized",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS visible asset state menu promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS visible asset state menu selected future decision")

    for key, expected in FALSE_FLAGS.items():
        if menu.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS visible asset state menu readiness promoted {key}")

    body = menu.get("visible_asset_state_internal_state_menu", {})
    if body.get("canonical_family") != "Visible Asset State Snapshot":
        raise CityOpsContractError("AAS visible asset state menu family drift")
    if body.get("legacy_source_family") != "field_asset_ops":
        raise CityOpsContractError("AAS visible asset state menu legacy family drift")
    if body.get("allowed_use") != "internal_admin_state_menu_only_no_asset_class_no_field_visit_no_customer_copy":
        raise CityOpsContractError("AAS visible asset state menu use drift")
    if body.get("menu_mode") != "state_menu_only":
        raise CityOpsContractError("AAS visible asset state menu mode drift")
    if body.get("still_blocked") is not True:
        raise CityOpsContractError("AAS visible asset state menu unblocked")
    if body.get("next_gate_before_any_delivery_or_runtime_movement") != (
        "separate_asset_class_method_boundary_and_operator_answer_receipt"
    ):
        raise CityOpsContractError("AAS visible asset state menu next gate drift")

    rows = body.get("state_menu_rows", [])
    row_codes = [row.get("state_code") for row in rows]
    if row_codes != REQUIRED_STATE_CODES:
        raise CityOpsContractError("AAS visible asset state menu state code drift")
    if body.get("required_state_codes") != REQUIRED_STATE_CODES:
        raise CityOpsContractError("AAS visible asset state menu required codes drift")
    allowed_truth_families = set(body.get("allowed_truth_families", []))
    for row in rows:
        for key in [
            "state_code",
            "allowed_observation_values",
            "safe_internal_read",
            "forbidden_promotion",
            "missing_truth_family",
        ]:
            if key not in row:
                raise CityOpsContractError(f"AAS visible asset state menu row missing {key}")
        if not row.get("allowed_observation_values"):
            raise CityOpsContractError("AAS visible asset state menu row empty values")
        if row.get("missing_truth_family") not in allowed_truth_families:
            raise CityOpsContractError("AAS visible asset state menu wrong truth family")
        forbidden = row.get("forbidden_promotion", "")
        for required_fragment in ["does_not", "or"]:
            if required_fragment not in forbidden:
                raise CityOpsContractError("AAS visible asset state menu weak forbidden promotion")

    safe = set(menu.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(menu.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS visible asset state menu safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS visible asset state menu forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS visible asset state menu missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"AAS visible asset state menu claim overlap: {sorted(overlap)}"
        )

    firewall = menu.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS visible asset state menu allowed {key}")
