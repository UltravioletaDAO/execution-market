"""Internal/admin AAS operator cockpit read surface.

This proof block consumes the current 4 AM pattern-synthesis handoff and turns
it into a compact cockpit-shaped, read-only internal/admin surface. It is not a
public dashboard, answer record, approval record, runtime change, product
surface, customer/worker copy, dispatch surface, reputation signal, payment
claim, or stopped-project integration.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_four_am_pattern_synthesis_handoff import (
    AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME,
    AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SAFE_CLAIM,
    AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SCHEMA,
    AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_STATUS,
    PATTERN_SYNTHESIS_BLOCKED_CLAIMS,
    PATTERN_SYNTHESIS_FALSE_FLAGS,
    load_aas_four_am_pattern_synthesis_handoff,
)
from .aas_two_lane_operator_answer_schema import (
    ALLOWED_FUTURE_DECISIONS,
    DEFAULT_EFFECTIVE_DECISION,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_OPERATOR_COCKPIT_READ_SURFACE_SCHEMA = "city_ops.aas_operator_cockpit_read_surface.v1"
AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME = "aas_operator_cockpit_read_surface.json"
AAS_OPERATOR_COCKPIT_READ_SURFACE_SAFE_CLAIM = (
    "internal_admin_aas_operator_cockpit_read_surface_landed"
)
AAS_OPERATOR_COCKPIT_READ_SURFACE_ID = (
    "execution_market.aas.operator_cockpit_read_surface.2026_06_04_2300"
)
AAS_OPERATOR_COCKPIT_READ_SURFACE_STATUS = (
    "read_only_operator_cockpit_no_answer_no_approval_no_runtime_or_external_promotion"
)

COCKPIT_PANES = [
    {
        "pane": "source_truth",
        "title": "Current AAS truth starts here",
        "displays": [
            "source_handoff_digest",
            "safe_claims",
            "blocked_claims",
            "stopped_project_firewall",
        ],
        "operator_use": "orient_before_any_future_answer_record",
    },
    {
        "pane": "allowed_answer_values",
        "title": "Exactly four allowed future values",
        "displays": ALLOWED_FUTURE_DECISIONS,
        "operator_use": "copy_one_value_into_a_separate_answer_record_if_explicitly_chosen",
    },
    {
        "pane": "runtime_blocker",
        "title": "Acontext/runtime current blocker",
        "displays": [
            "docker_daemon_unreachable_on_user_socket",
            "local_acontext_api_core_ui_unverified",
            "historical_fixtures_are_not_current_runtime_truth",
        ],
        "operator_use": "prevent_runtime_memory_claims_until_rechecked_after_docker_recovery",
    },
    {
        "pane": "product_exposure_blocker",
        "title": "Retail Reality / product exposure blocker",
        "displays": [
            "no_retail_reality_answer_or_hold_record",
            "no_customer_public_worker_surface",
            "no_catalog_pricing_queue_or_dispatch_authority",
        ],
        "operator_use": "prevent_catalog_or_customer_copy_from_internal_planning_docs",
    },
    {
        "pane": "recommended_no_answer_posture",
        "title": "Safe default with no explicit answer",
        "displays": ["pause_aas_proof_layering", "keep_both_lanes_held"],
        "operator_use": "stop_accidental_no_answer_ceremony_and_keep_both_lanes_held",
    },
]

COCKPIT_FALSE_FLAGS = {
    "cockpit_records_operator_answer": False,
    "cockpit_records_operator_approval": False,
    "cockpit_selects_future_answer": False,
    "cockpit_creates_answer_record": False,
    "cockpit_treats_display_as_approval": False,
    "cockpit_approves_product_exposure": False,
    "cockpit_approves_runtime_memory_wiring": False,
    "cockpit_registers_runtime_adapter": False,
    "cockpit_enables_runtime_adapter": False,
    "cockpit_mutates_irc_session_manager": False,
    "cockpit_writes_live_acontext": False,
    "cockpit_retrieves_live_acontext": False,
    "cockpit_enables_cross_project_autorouting": False,
    "cockpit_creates_customer_copy": False,
    "cockpit_creates_worker_instruction": False,
    "cockpit_creates_public_dashboard": False,
    "cockpit_enables_catalog_pricing_queue_or_dispatch": False,
    "cockpit_emits_erc8004_reputation": False,
    "cockpit_emits_worker_skill_dna": False,
    "cockpit_reverifies_payment_or_production": False,
    "cockpit_releases_exact_gps_or_raw_metadata": False,
    "cockpit_releases_private_context": False,
    "cockpit_grants_domain_authority_claims": False,
    "cockpit_publishes_worker_copyable_doctrine": False,
    "cockpit_integrates_stopped_projects": False,
}

COCKPIT_BLOCKED_CLAIMS = [
    *PATTERN_SYNTHESIS_BLOCKED_CLAIMS,
    "operator_cockpit_records_operator_answer",
    "operator_cockpit_records_operator_approval",
    "operator_cockpit_selects_future_answer",
    "operator_cockpit_creates_answer_record",
    "operator_cockpit_treats_display_as_approval",
    "operator_cockpit_approves_product_exposure",
    "operator_cockpit_approves_runtime_memory_wiring",
    "operator_cockpit_registers_or_enables_runtime_adapter",
    "operator_cockpit_mutates_irc_session_manager",
    "operator_cockpit_writes_or_retrieves_live_acontext",
    "operator_cockpit_authorizes_cross_project_autorouting",
    "operator_cockpit_creates_customer_public_worker_surface",
    "operator_cockpit_creates_public_dashboard_or_metric",
    "operator_cockpit_authorizes_catalog_pricing_queue_or_dispatch",
    "operator_cockpit_emits_erc8004_reputation_or_worker_skill_dna",
    "operator_cockpit_reverifies_payment_or_production",
    "operator_cockpit_releases_exact_gps_or_raw_metadata",
    "operator_cockpit_releases_private_context",
    "operator_cockpit_grants_domain_authority_claims",
    "operator_cockpit_publishes_worker_copyable_doctrine",
    "operator_cockpit_integrates_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(COCKPIT_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "future_answer_selected",
    "answer_record_created",
    "product_exposure_approved",
    "runtime_memory_wiring_approved",
    "runtime_adapter_registered",
    "runtime_adapter_enabled",
    "irc_session_manager_mutated",
    "live_acontext_ready",
    "runtime_parity_proven",
    "cross_project_autorouting_ready",
    "customer_copy_ready",
    "public_dashboard_ready",
    "catalog_ready",
    "pricing_ready",
    "dispatch_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
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


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _assert_source_handoff(handoff: dict[str, Any]) -> None:
    if handoff.get("schema") != AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SCHEMA:
        raise CityOpsContractError("AAS operator cockpit source handoff schema drift")
    if handoff.get("handoff_status") != AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_STATUS:
        raise CityOpsContractError("AAS operator cockpit source handoff status drift")
    safe = set(handoff.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS operator cockpit source safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS operator cockpit source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    blocked = set(handoff.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(PATTERN_SYNTHESIS_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS operator cockpit source missing blocked claims: {sorted(missing)}"
        )
    current = handoff.get("current_no_answer_decision", {})
    if current.get("operator_answer_recorded") is not False:
        raise CityOpsContractError("AAS operator cockpit source recorded operator answer")
    if current.get("operator_approval_recorded") is not False:
        raise CityOpsContractError("AAS operator cockpit source recorded operator approval")
    if current.get("selected_future_answer") is not None:
        raise CityOpsContractError("AAS operator cockpit source selected future answer")
    if current.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS operator cockpit source effective decision drift")
    readiness = handoff.get("readiness", {})
    for key, expected in PATTERN_SYNTHESIS_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS operator cockpit source promoted readiness {key}")
    firewall = handoff.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS operator cockpit source allowed {key}")


def build_aas_operator_cockpit_read_surface(
    *,
    artifact_dir: str | Path | None = None,
    source_handoff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin AAS operator cockpit read surface."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    handoff = source_handoff or load_aas_four_am_pattern_synthesis_handoff(
        artifact_dir=source_dir
    )
    _assert_source_handoff(handoff)

    safe_to_claim = _dedupe(
        [
            *handoff["claim_boundaries"]["safe_to_claim"],
            AAS_OPERATOR_COCKPIT_READ_SURFACE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *handoff["claim_boundaries"]["do_not_claim_yet"],
            *COCKPIT_BLOCKED_CLAIMS,
        ]
    )

    cockpit = {
        "schema": AAS_OPERATOR_COCKPIT_READ_SURFACE_SCHEMA,
        "cockpit_id": AAS_OPERATOR_COCKPIT_READ_SURFACE_ID,
        "scope": "internal_admin_read_only_aas_operator_cockpit",
        "cockpit_status": AAS_OPERATOR_COCKPIT_READ_SURFACE_STATUS,
        "source_policy": "consume_current_4am_pattern_synthesis_handoff_only",
        "source_handoff": {
            "file": AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME,
            "schema": handoff["schema"],
            "handoff_id": handoff["handoff_id"],
            "safe_claim": AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_SAFE_CLAIM,
            "digest_sha256": _stable_digest(handoff),
            "effective_decision": handoff["current_no_answer_decision"][
                "effective_decision"
            ],
        },
        "cockpit_panes": [
            {
                **pane,
                "internal_admin_read_only": True,
                "selected_by_this_cockpit": False,
                "approval_granted_by_this_cockpit": False,
                "runtime_or_external_promotion_allowed": False,
            }
            for pane in COCKPIT_PANES
        ],
        "answer_panel": {
            "allowed_future_decisions": [
                {
                    "decision": decision,
                    "displayed_by_this_cockpit": True,
                    "selected_by_this_cockpit": False,
                    "requires_separate_answer_record": True,
                    "approval_granted_by_this_cockpit": False,
                }
                for decision in ALLOWED_FUTURE_DECISIONS
            ],
            "recommended_no_answer_values": [
                "pause_aas_proof_layering",
                "keep_both_lanes_held",
            ],
            "default_if_no_human_answer": DEFAULT_EFFECTIVE_DECISION,
            "display_text_is_not_answer": True,
        },
        "current_no_answer_decision": {
            "operator_answer_recorded": False,
            "operator_approval_recorded": False,
            "selected_future_answer": None,
            "effective_decision": DEFAULT_EFFECTIVE_DECISION,
            "cockpit_display_is_approval": False,
            "cockpit_is_answer_record": False,
        },
        "runtime_blocker_snapshot": {
            "docker_context_observed": "desktop-linux",
            "docker_daemon_reachable": False,
            "local_acontext_3000_reachable": False,
            "local_acontext_8080_reachable": False,
            "local_acontext_5173_reachable": False,
            "snapshot_is_runtime_repair": False,
            "snapshot_claims_runtime_parity": False,
        },
        "readiness": {
            "internal_admin_operator_cockpit_read_surface_landed": True,
            "source_handoff_verified": True,
            "cockpit_panes_renderable_from_existing_artifacts": True,
            "answer_panel_displayed_without_selection": True,
            "default_off_non_authorizing": True,
            **COCKPIT_FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "still_blocked_claims": do_not_claim_yet,
        "stopped_project_firewall": {
            "autojob_work_allowed": False,
            "frontier_academy_work_allowed": False,
            "kk_v2_work_allowed": False,
            "karmacadabra_v2_work_allowed": False,
            "source": "DREAM-PRIORITIES.md explicit stop list",
        },
        "operator_guidance": {
            "first_read": "DREAM-PRIORITIES.md",
            "use_this_cockpit_for": "internal_admin_read_only_orientation_only",
            "if_no_real_answer": "pause_proof_layering_or_keep_both_lanes_held",
            "if_real_answer_exists": "create_separate_two_lane_operator_answer_record_first",
            "not_public_dashboard": True,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "not_runtime_adapter": True,
        },
        "cockpit_verdict": (
            "operator_cockpit_read_surface_landed_no_answer_no_approval_display_only_"
            "existing_artifacts_rendered_as_internal_admin_orientation_no_runtime_product_"
            "reputation_payment_dispatch_public_dashboard_or_stopped_project_promotion"
        ),
    }
    _assert_aas_operator_cockpit_read_surface(cockpit, source_handoff=handoff)
    return cockpit


def _assert_aas_operator_cockpit_read_surface(
    cockpit: dict[str, Any], *, source_handoff: dict[str, Any]
) -> None:
    _assert_source_handoff(source_handoff)
    if cockpit.get("schema") != AAS_OPERATOR_COCKPIT_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("AAS operator cockpit schema drift")
    if cockpit.get("cockpit_id") != AAS_OPERATOR_COCKPIT_READ_SURFACE_ID:
        raise CityOpsContractError("AAS operator cockpit id drift")
    if cockpit.get("cockpit_status") != AAS_OPERATOR_COCKPIT_READ_SURFACE_STATUS:
        raise CityOpsContractError("AAS operator cockpit status drift")
    source = cockpit.get("source_handoff", {})
    if source.get("file") != AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_FILENAME:
        raise CityOpsContractError("AAS operator cockpit source file drift")
    if source.get("digest_sha256") != _stable_digest(source_handoff):
        raise CityOpsContractError("AAS operator cockpit source digest drift")
    if source.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS operator cockpit source effective decision drift")

    panes = cockpit.get("cockpit_panes", [])
    if [pane.get("pane") for pane in panes] != [pane["pane"] for pane in COCKPIT_PANES]:
        raise CityOpsContractError("AAS operator cockpit pane drift")
    for pane in panes:
        if pane.get("internal_admin_read_only") is not True:
            raise CityOpsContractError("AAS operator cockpit pane not read-only")
        for key in [
            "selected_by_this_cockpit",
            "approval_granted_by_this_cockpit",
            "runtime_or_external_promotion_allowed",
        ]:
            if pane.get(key) is not False:
                raise CityOpsContractError(f"AAS operator cockpit pane promoted {key}")

    answer_panel = cockpit.get("answer_panel", {})
    decisions = answer_panel.get("allowed_future_decisions", [])
    if [item.get("decision") for item in decisions] != ALLOWED_FUTURE_DECISIONS:
        raise CityOpsContractError("AAS operator cockpit decision options drift")
    if answer_panel.get("default_if_no_human_answer") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS operator cockpit default decision drift")
    if answer_panel.get("display_text_is_not_answer") is not True:
        raise CityOpsContractError("AAS operator cockpit display text became answer")
    for item in decisions:
        if item.get("displayed_by_this_cockpit") is not True:
            raise CityOpsContractError("AAS operator cockpit decision not displayed")
        if item.get("selected_by_this_cockpit") is not False:
            raise CityOpsContractError("AAS operator cockpit selected decision")
        if item.get("requires_separate_answer_record") is not True:
            raise CityOpsContractError("AAS operator cockpit decision missing answer record gate")
        if item.get("approval_granted_by_this_cockpit") is not False:
            raise CityOpsContractError("AAS operator cockpit granted approval")

    current = cockpit.get("current_no_answer_decision", {})
    for key in [
        "operator_answer_recorded",
        "operator_approval_recorded",
        "cockpit_display_is_approval",
        "cockpit_is_answer_record",
    ]:
        if current.get(key) is not False:
            raise CityOpsContractError(f"AAS operator cockpit promoted {key}")
    if current.get("selected_future_answer") is not None:
        raise CityOpsContractError("AAS operator cockpit selected future answer")
    if current.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS operator cockpit effective decision drift")

    blocker = cockpit.get("runtime_blocker_snapshot", {})
    for key in [
        "docker_daemon_reachable",
        "local_acontext_3000_reachable",
        "local_acontext_8080_reachable",
        "local_acontext_5173_reachable",
        "snapshot_is_runtime_repair",
        "snapshot_claims_runtime_parity",
    ]:
        if blocker.get(key) is not False:
            raise CityOpsContractError(f"AAS operator cockpit runtime blocker promoted {key}")

    readiness = cockpit.get("readiness", {})
    for key, expected in COCKPIT_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS operator cockpit promoted readiness {key}")

    safe = set(cockpit.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(cockpit.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_OPERATOR_COCKPIT_READ_SURFACE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS operator cockpit safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS operator cockpit forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(COCKPIT_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS operator cockpit missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(f"AAS operator cockpit claim overlap: {sorted(overlap)}")
    if cockpit.get("still_blocked_claims") != cockpit.get("claim_boundaries", {}).get(
        "do_not_claim_yet"
    ):
        raise CityOpsContractError("AAS operator cockpit blocked claims drift")

    firewall = cockpit.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS operator cockpit allowed {key}")


def write_aas_operator_cockpit_read_surface(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    cockpit = build_aas_operator_cockpit_read_surface(artifact_dir=target_dir)
    target_path = target_dir / AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME
    target_path.write_text(
        json.dumps(cockpit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target_path


def load_aas_operator_cockpit_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME
    cockpit = json.loads(path.read_text(encoding="utf-8"))
    handoff = load_aas_four_am_pattern_synthesis_handoff(artifact_dir=source_dir)
    _assert_aas_operator_cockpit_read_surface(cockpit, source_handoff=handoff)
    return cockpit
