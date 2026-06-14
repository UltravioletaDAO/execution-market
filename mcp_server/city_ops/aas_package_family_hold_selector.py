"""Internal/admin AAS package-family hold selector.

This slice consumes the latest held package-family artifacts and makes the
no-answer posture explicit: Bounded Local Count is the only family with a
next operator value gate, while Visible Asset State Snapshot and Pre-Event
Blocker Check stay as internal/admin grammars only. It is not an operator
answer, approval record, answer receipt, customer/worker/public copy, route,
queue, dispatch, runtime mutation, reputation event, payment/production change,
location/private-context release, authority claim, or stopped-project bridge.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_bounded_local_count_fixture_gate import (
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SCHEMA,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_STATUS,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_BLOCKED_CLAIMS,
    load_aas_bounded_local_count_fixture_gate,
)
from .aas_pre_event_blocker_internal_checklist import (
    AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_FILENAME,
    AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SAFE_CLAIM,
    AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SCHEMA,
    AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_STATUS,
    PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_BLOCKED_CLAIMS,
    REQUIRED_CHECK_CODES,
    load_aas_pre_event_blocker_internal_checklist,
)
from .aas_visible_asset_state_internal_state_menu import (
    AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_FILENAME,
    AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SAFE_CLAIM,
    AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SCHEMA,
    AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_STATUS,
    REQUIRED_STATE_CODES,
    VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_BLOCKED_CLAIMS,
    load_aas_visible_asset_state_internal_state_menu,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SCHEMA = "city_ops.aas_package_family_hold_selector.v1"
AAS_PACKAGE_FAMILY_HOLD_SELECTOR_FILENAME = "aas_package_family_hold_selector.json"
AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SAFE_CLAIM = (
    "internal_admin_aas_package_family_hold_selector_landed"
)
AAS_PACKAGE_FAMILY_HOLD_SELECTOR_ID = (
    "execution_market.aas.package_family_hold_selector.2026_06_14_0300"
)
AAS_PACKAGE_FAMILY_HOLD_SELECTOR_STATUS = (
    "internal_admin_hold_selector_no_answer_no_approval_no_collection_runtime_dispatch_or_payment"
)

RECOMMENDED_BOUNDED_LOCAL_COUNT_VALUE = (
    "bounded_local_count.visible_posted_state_count.v1"
)

FALSE_FLAGS = {
    "selector_records_operator_answer": False,
    "selector_records_operator_approval": False,
    "selector_creates_answer_receipt": False,
    "selector_selects_future_answer": False,
    "selector_approves_product_exposure": False,
    "selector_authorizes_collection_or_site_access": False,
    "selector_creates_customer_public_or_worker_copy": False,
    "selector_creates_catalog_pricing_quote_route_queue_or_dispatch": False,
    "selector_creates_worker_instruction": False,
    "selector_mutates_runtime_acontext_irc_or_session_manager": False,
    "selector_emits_reputation_or_worker_skill_dna": False,
    "selector_reverifies_payment_production_or_chain_state": False,
    "selector_releases_exact_gps_raw_metadata_private_context_or_pii": False,
    "selector_grants_domain_legal_safety_repair_insurance_permit_or_sla_authority": False,
    "selector_publishes_worker_copyable_doctrine": False,
    "selector_integrates_or_expands_stopped_projects": False,
}

PACKAGE_FAMILY_ROWS = [
    {
        "canonical_family": "Bounded Local Count",
        "source_artifact_key": "bounded_local_count_fixture_gate",
        "current_state": "fixture_gate_ready_needs_one_explicit_operator_value",
        "allowed_next_gate": "separate_operator_value_then_digest_backed_answer_receipt",
        "recommended_value_if_human_chooses_to_move": RECOMMENDED_BOUNDED_LOCAL_COUNT_VALUE,
        "hold_reason_without_answer": "fixture_depth_is_not_authorization",
        "forbidden_promotion": "does_not_create_collection_customer_copy_route_dispatch_reputation_payment_runtime_or_authority_claim",
    },
    {
        "canonical_family": "Visible Asset State Snapshot",
        "source_artifact_key": "visible_asset_state_internal_state_menu",
        "current_state": "internal_state_menu_only",
        "allowed_next_gate": "hold_until_separate_asset_class_collection_method_and_operator_answer_receipt",
        "recommended_value_if_human_chooses_to_move": None,
        "hold_reason_without_answer": "state_options_are_not_field_access_or_repair_authority",
        "forbidden_promotion": "does_not_create_asset_visit_customer_copy_route_dispatch_reputation_payment_runtime_or_authority_claim",
    },
    {
        "canonical_family": "Pre-Event Blocker Check",
        "source_artifact_key": "pre_event_blocker_internal_checklist",
        "current_state": "internal_checklist_only",
        "allowed_next_gate": "hold_until_separate_event_type_observation_window_and_operator_answer_receipt",
        "recommended_value_if_human_chooses_to_move": None,
        "hold_reason_without_answer": "checklist_options_are_not_event_site_access_or_permit_security_authority",
        "forbidden_promotion": "does_not_create_event_site_access_customer_copy_route_dispatch_reputation_payment_runtime_or_authority_claim",
    },
]

SYSTEM_INTEGRATION_HOLD_CONNECTIONS = [
    {
        "connection": "memory_system_to_acontext",
        "safe_now": "carry reviewed safe_claims blocked_claims source_digests and selected_posture only",
        "blocked_until_gate": "no live Acontext write retrieve runtime parity or memory mutation",
        "success_metric": "digest_and_blocked_claim_preservation",
    },
    {
        "connection": "irc_session_management",
        "safe_now": "emit read_only handoff capsule fields for family posture and next gate",
        "blocked_until_gate": "no IRC session manager mutation routing queue or agent assignment",
        "success_metric": "handoff_fields_do_not_select_or_route_work",
    },
    {
        "connection": "cross_project_decision_support",
        "safe_now": "filter stale cron payloads and show only AAS hold_or_bounded_count_answer paths",
        "blocked_until_gate": "no AutoJob Frontier Academy KK_v2 or KarmaCadabra_v2 integration",
        "success_metric": "stopped_project_firewall_stays_false",
    },
    {
        "connection": "agent_observability_success_metrics",
        "safe_now": "track no_answer_discipline package_family_hold and one_next_gate clarity",
        "blocked_until_gate": "no public dashboard customer promise or payment production metric",
        "success_metric": "selector_records_zero_promoted_readiness_flags",
    },
    {
        "connection": "payment_and_production_maturity",
        "safe_now": "carry as future launch prerequisite context only",
        "blocked_until_gate": "no payment chain production or 8_chain_reverification from this selector",
        "success_metric": "payment_reverification_flag_remains_false",
    },
]

PACKAGE_FAMILY_HOLD_SELECTOR_BLOCKED_CLAIMS = [
    *AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_BLOCKED_CLAIMS,
    *VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_BLOCKED_CLAIMS,
    *PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_BLOCKED_CLAIMS,
    "package_family_hold_selector_records_operator_answer",
    "package_family_hold_selector_records_operator_approval",
    "package_family_hold_selector_creates_answer_receipt",
    "package_family_hold_selector_selects_future_answer",
    "package_family_hold_selector_treats_package_menu_depth_as_authorization",
    "package_family_hold_selector_approves_product_exposure",
    "package_family_hold_selector_authorizes_collection_site_access_or_event_site_access",
    "package_family_hold_selector_creates_customer_public_or_worker_copy",
    "package_family_hold_selector_creates_catalog_pricing_quote_route_queue_or_dispatch",
    "package_family_hold_selector_creates_worker_instruction",
    "package_family_hold_selector_mutates_runtime_acontext_irc_or_session_manager",
    "package_family_hold_selector_emits_erc8004_reputation_or_worker_skill_dna",
    "package_family_hold_selector_reverifies_payment_production_or_chain_state",
    "package_family_hold_selector_releases_exact_gps_raw_metadata_private_context_or_pii",
    "package_family_hold_selector_grants_domain_legal_safety_repair_insurance_permit_or_sla_authority",
    "package_family_hold_selector_publishes_worker_copyable_doctrine",
    "package_family_hold_selector_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(PACKAGE_FAMILY_HOLD_SELECTOR_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "future_answer_selected",
    "collection_authorized",
    "field_visit_authorized",
    "event_site_access_authorized",
    "customer_copy_ready",
    "public_catalog_ready",
    "pricing_ready",
    "queue_ready",
    "dispatch_ready",
    "worker_instruction_ready",
    "runtime_parity_proven",
    "live_acontext_ready",
    "irc_session_manager_mutated",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "raw_metadata_release_ready",
    "private_context_release_ready",
    "pii_release_ready",
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


def build_aas_package_family_hold_selector(
    *,
    artifact_dir: str | Path | None = None,
    bounded_gate: dict[str, Any] | None = None,
    visible_menu: dict[str, Any] | None = None,
    pre_event_checklist: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic package-family hold selector."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    bounded = bounded_gate or load_aas_bounded_local_count_fixture_gate(
        artifact_dir=source_dir
    )
    visible = visible_menu or load_aas_visible_asset_state_internal_state_menu(
        artifact_dir=source_dir
    )
    pre_event = pre_event_checklist or load_aas_pre_event_blocker_internal_checklist(
        artifact_dir=source_dir
    )

    _assert_bounded_gate(bounded)
    _assert_visible_menu(visible)
    _assert_pre_event_checklist(pre_event)

    safe_to_claim = _dedupe(
        [
            *bounded["claim_boundaries"]["safe_to_claim"],
            *visible["claim_boundaries"]["safe_to_claim"],
            *pre_event["claim_boundaries"]["safe_to_claim"],
            AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM,
            AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SAFE_CLAIM,
            AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SAFE_CLAIM,
            AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *bounded["claim_boundaries"]["do_not_claim_yet"],
            *visible["claim_boundaries"]["do_not_claim_yet"],
            *pre_event["claim_boundaries"]["do_not_claim_yet"],
            *PACKAGE_FAMILY_HOLD_SELECTOR_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    selector: dict[str, Any] = {
        "schema": AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SCHEMA,
        "selector_id": AAS_PACKAGE_FAMILY_HOLD_SELECTOR_ID,
        "selector_status": AAS_PACKAGE_FAMILY_HOLD_SELECTOR_STATUS,
        "source_artifacts": {
            "bounded_local_count_fixture_gate": {
                "file": AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME,
                "schema": bounded["schema"],
                "status": bounded["gate_status"],
                "safe_claim": AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(bounded),
            },
            "visible_asset_state_internal_state_menu": {
                "file": AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_FILENAME,
                "schema": visible["schema"],
                "status": visible["state_menu_status"],
                "safe_claim": AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SAFE_CLAIM,
                "digest_sha256": _stable_digest(visible),
                "required_state_codes": list(REQUIRED_STATE_CODES),
            },
            "pre_event_blocker_internal_checklist": {
                "file": AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_FILENAME,
                "schema": pre_event["schema"],
                "status": pre_event["checklist_status"],
                "safe_claim": AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SAFE_CLAIM,
                "digest_sha256": _stable_digest(pre_event),
                "required_check_codes": list(REQUIRED_CHECK_CODES),
            },
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service internal/admin planning",
            "source_precedence": "dream_priorities_wins_over_stale_cron_payload",
            "stopped_project_firewall": {
                "autojob_work_allowed": False,
                "frontier_academy_work_allowed": False,
                "kk_v2_work_allowed": False,
                "karmacadabra_v2_work_allowed": False,
            },
        },
        "package_family_rows": [dict(row) for row in PACKAGE_FAMILY_ROWS],
        "system_integration_hold_connections": [
            dict(connection) for connection in SYSTEM_INTEGRATION_HOLD_CONNECTIONS
        ],
        "current_operator_state": {
            "explicit_operator_answer_available": False,
            "operator_approval_recorded": False,
            "answer_receipt_created": False,
            "selected_package_family": None,
            "selected_value": None,
            "recommended_single_next_value_if_human_moves": RECOMMENDED_BOUNDED_LOCAL_COUNT_VALUE,
            "selected_posture_now": "pause_aas_proof_layering",
        },
        "allowed_next_actions": [
            {
                "condition": "no_real_operator_answer_exists",
                "action": "hold_pause_aas_proof_layering_and_stop_adding_package_menus",
                "allowed_now": True,
            },
            {
                "condition": "bounded_local_count_operator_value_arrives",
                "action": "create_one_separate_digest_backed_answer_receipt_before_any_downstream_gate",
                "allowed_now": False,
            },
            {
                "condition": "visible_asset_or_pre_event_family_requested_later",
                "action": "require_separate_family_specific_operator_answer_receipt_before_collection_or_runtime_movement",
                "allowed_now": False,
            },
            {
                "condition": "future_cron_mentions_stopped_projects",
                "action": "read_dream_priorities_first_and_skip_stopped_project_work",
                "allowed_now": True,
            },
        ],
        "readiness": {
            "package_family_hold_selector_landed": True,
            "source_artifacts_verified": True,
            "single_next_gate_named": True,
            "system_integration_connections_are_read_only": True,
            **FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "selector_digest_sha256": "",
    }
    selector["selector_digest_sha256"] = _stable_digest(
        {k: v for k, v in selector.items() if k != "selector_digest_sha256"}
    )
    _assert_aas_package_family_hold_selector(
        selector,
        bounded_gate=bounded,
        visible_menu=visible,
        pre_event_checklist=pre_event,
    )
    return selector


def _assert_bounded_gate(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SCHEMA:
        raise CityOpsContractError("AAS package hold selector bounded gate schema drift")
    if packet.get("gate_status") != AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_STATUS:
        raise CityOpsContractError("AAS package hold selector bounded gate status drift")
    for key, value in packet.get("readiness", {}).items():
        if key.startswith("gate_") and value is not False:
            raise CityOpsContractError(f"AAS package hold selector bounded gate promoted {key}")


def _assert_visible_menu(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SCHEMA:
        raise CityOpsContractError("AAS package hold selector visible menu schema drift")
    if packet.get("state_menu_status") != AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_STATUS:
        raise CityOpsContractError("AAS package hold selector visible menu status drift")
    rows = packet.get("visible_asset_state_internal_state_menu", {}).get(
        "state_menu_rows", []
    )
    if [row.get("state_code") for row in rows] != REQUIRED_STATE_CODES:
        raise CityOpsContractError("AAS package hold selector visible menu state code drift")


def _assert_pre_event_checklist(packet: dict[str, Any]) -> None:
    if packet.get("schema") != AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SCHEMA:
        raise CityOpsContractError("AAS package hold selector pre-event checklist schema drift")
    if packet.get("checklist_status") != AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_STATUS:
        raise CityOpsContractError("AAS package hold selector pre-event checklist status drift")
    rows = packet.get("pre_event_blocker_internal_checklist", {}).get(
        "checklist_rows", []
    )
    if [row.get("check_code") for row in rows] != REQUIRED_CHECK_CODES:
        raise CityOpsContractError("AAS package hold selector pre-event checklist code drift")


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"AAS package hold selector claim overlap: {sorted(overlap)}"
        )
    forbidden_safe = set(safe_to_claim) & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS package hold selector forbidden safe claims: {sorted(forbidden_safe)}"
        )


def _assert_aas_package_family_hold_selector(
    selector: dict[str, Any],
    *,
    bounded_gate: dict[str, Any],
    visible_menu: dict[str, Any],
    pre_event_checklist: dict[str, Any],
) -> None:
    _assert_bounded_gate(bounded_gate)
    _assert_visible_menu(visible_menu)
    _assert_pre_event_checklist(pre_event_checklist)
    if selector.get("schema") != AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SCHEMA:
        raise CityOpsContractError("AAS package hold selector schema drift")
    if selector.get("selector_status") != AAS_PACKAGE_FAMILY_HOLD_SELECTOR_STATUS:
        raise CityOpsContractError("AAS package hold selector status drift")

    sources = selector.get("source_artifacts", {})
    if sources.get("bounded_local_count_fixture_gate", {}).get("digest_sha256") != _stable_digest(bounded_gate):
        raise CityOpsContractError("AAS package hold selector bounded gate digest drift")
    if sources.get("visible_asset_state_internal_state_menu", {}).get("digest_sha256") != _stable_digest(visible_menu):
        raise CityOpsContractError("AAS package hold selector visible menu digest drift")
    if sources.get("pre_event_blocker_internal_checklist", {}).get("digest_sha256") != _stable_digest(pre_event_checklist):
        raise CityOpsContractError("AAS package hold selector pre-event checklist digest drift")

    if selector.get("package_family_rows") != PACKAGE_FAMILY_ROWS:
        raise CityOpsContractError("AAS package hold selector package family row drift")
    if selector.get("system_integration_hold_connections") != SYSTEM_INTEGRATION_HOLD_CONNECTIONS:
        raise CityOpsContractError("AAS package hold selector system connection drift")

    operator = selector.get("current_operator_state", {})
    if operator.get("explicit_operator_answer_available") is not False:
        raise CityOpsContractError("AAS package hold selector recorded operator answer")
    if operator.get("operator_approval_recorded") is not False:
        raise CityOpsContractError("AAS package hold selector recorded operator approval")
    if operator.get("answer_receipt_created") is not False:
        raise CityOpsContractError("AAS package hold selector created answer receipt")
    if operator.get("selected_value") is not None:
        raise CityOpsContractError("AAS package hold selector selected a value")
    if operator.get("selected_posture_now") != "pause_aas_proof_layering":
        raise CityOpsContractError("AAS package hold selector posture drift")

    readiness = selector.get("readiness", {})
    for key, expected in FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS package hold selector promoted {key}")

    actions = selector.get("allowed_next_actions", [])
    by_condition = {action.get("condition"): action for action in actions}
    if by_condition.get("no_real_operator_answer_exists", {}).get("allowed_now") is not True:
        raise CityOpsContractError("AAS package hold selector hold action drift")
    for condition in [
        "bounded_local_count_operator_value_arrives",
        "visible_asset_or_pre_event_family_requested_later",
    ]:
        if by_condition.get(condition, {}).get("allowed_now") is not False:
            raise CityOpsContractError("AAS package hold selector next action promoted")

    firewall = selector.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS package hold selector allowed {key}")

    safe = set(selector.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(selector.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_PACKAGE_FAMILY_HOLD_SELECTOR_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS package hold selector safe claim missing")
    missing = set(PACKAGE_FAMILY_HOLD_SELECTOR_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS package hold selector missing blocked claims: {sorted(missing)}"
        )
    _assert_no_claim_overlap(list(safe), list(blocked))
    digest = selector.get("selector_digest_sha256")
    expected = _stable_digest({k: v for k, v in selector.items() if k != "selector_digest_sha256"})
    if digest != expected:
        raise CityOpsContractError("AAS package hold selector digest drift")


def write_aas_package_family_hold_selector(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    selector = build_aas_package_family_hold_selector(artifact_dir=target_dir)
    target_path = target_dir / AAS_PACKAGE_FAMILY_HOLD_SELECTOR_FILENAME
    target_path.write_text(
        json.dumps(selector, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target_path


def load_aas_package_family_hold_selector(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_PACKAGE_FAMILY_HOLD_SELECTOR_FILENAME
    selector = json.loads(path.read_text(encoding="utf-8"))
    bounded = load_aas_bounded_local_count_fixture_gate(artifact_dir=source_dir)
    visible = load_aas_visible_asset_state_internal_state_menu(artifact_dir=source_dir)
    pre_event = load_aas_pre_event_blocker_internal_checklist(artifact_dir=source_dir)
    _assert_aas_package_family_hold_selector(
        selector,
        bounded_gate=bounded,
        visible_menu=visible,
        pre_event_checklist=pre_event,
    )
    return selector
