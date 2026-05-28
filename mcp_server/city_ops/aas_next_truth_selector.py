"""Internal/admin next-truth selector for AAS coordination.

The route regret panel says to stop adding internal route layers until new
runtime truth or operator truth exists.  The exponential-value pathfinder says
runtime memory/Acontext prerequisites are the highest multiplier.  The
activation board says those prerequisites are still not live-ready.

This module joins those three conservative artifacts into one selector: the
next valuable work is prerequisite/runtime-truth work, not another route, not a
customer surface, and not dispatch/reputation/payment/production/GPS/worker
copyable doctrine.  It is read-only and internal/admin only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_exponential_value_pathfinder import (
    AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME,
    AAS_EXPONENTIAL_VALUE_PATHFINDER_SAFE_CLAIM,
    AAS_EXPONENTIAL_VALUE_PATHFINDER_SCHEMA,
    EXPONENTIAL_VALUE_BLOCKED_CLAIMS,
    load_aas_exponential_value_pathfinder,
)
from .aas_system_integration_flywheel_route_regret_panel import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SCHEMA,
    REGRET_PANEL_BLOCKED_CLAIMS,
    REGRET_PANEL_DEFAULT_OUTCOME,
    REGRET_PANEL_VERDICT,
    load_aas_system_integration_flywheel_route_regret_panel,
)
from .acontext_prerequisite_activation_board import (
    ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME,
    ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SAFE_CLAIM,
    ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SCHEMA,
    ACTIVATION_BOARD_BLOCKED_CLAIMS,
    load_acontext_prerequisite_activation_board,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_NEXT_TRUTH_SELECTOR_SCHEMA = "city_ops.aas_next_truth_selector.v1"
AAS_NEXT_TRUTH_SELECTOR_FILENAME = "aas_next_truth_selector.json"
AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM = "admin_aas_next_truth_selector_landed"

SELECTOR_VERDICT = "select_runtime_prerequisite_truth_not_more_route_layers"
SELECTED_NEXT_TRACK = "runtime_truth_prerequisite_activation"
SELECTED_NEXT_PROOF = "clear_acontext_sdk_api_dashboard_then_rerun_read_only_preflight"

SELECTOR_BLOCKED_CLAIMS = [
    *EXPONENTIAL_VALUE_BLOCKED_CLAIMS,
    *ACTIVATION_BOARD_BLOCKED_CLAIMS,
    *REGRET_PANEL_BLOCKED_CLAIMS,
    "next_truth_selector_authorizes_more_route_layers",
    "next_truth_selector_authorizes_customer_copy_or_delivery",
    "next_truth_selector_authorizes_public_or_catalog_route",
    "next_truth_selector_authorizes_queue_launch_or_dispatch",
    "next_truth_selector_authorizes_pricing_or_customer_quote",
    "next_truth_selector_authorizes_erc8004_reputation_or_worker_skill_dna",
    "next_truth_selector_authorizes_live_acontext_write_or_retrieve",
    "next_truth_selector_proves_runtime_parity",
    "next_truth_selector_reverifies_payment_or_production",
    "next_truth_selector_allows_exact_gps_or_raw_metadata",
    "next_truth_selector_grants_domain_or_emergency_authority",
    "next_truth_selector_creates_worker_copyable_doctrine",
    "next_truth_selector_turns_pattern_recognition_into_autopilot",
]

_FALSE_ACCESS_FLAGS = [
    "network_route_registered",
    "public_route_registered",
    "customer_visible",
    "worker_visible",
    "operator_queue_launched",
    "dispatch_enabled",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "writes_customer_copy",
    "emits_reputation_receipts",
    "reverifies_payment_coverage",
    "reverifies_production_infrastructure",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_READINESS_FLAGS = [
    "selector_promotes_live_readiness",
    "more_route_layers_allowed",
    "customer_copy_ready",
    "customer_delivery_ready",
    "public_or_catalog_route_ready",
    "operator_queue_launch_ready",
    "dispatch_ready",
    "pricing_or_customer_quote_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "live_acontext_write_allowed",
    "live_acontext_retrieve_allowed",
    "runtime_parity_proven",
    "ready_to_attempt_live_transport",
    "payment_coverage_reverified_by_this_selector",
    "production_infrastructure_reverified_by_this_selector",
    "gps_or_metadata_exposure_allowed",
    "domain_or_emergency_authority_ready",
    "worker_copyable_doctrine_ready",
]


def build_aas_next_truth_selector(
    *,
    artifact_dir: str | Path | None = None,
    pathfinder: dict[str, Any] | None = None,
    activation_board: dict[str, Any] | None = None,
    regret_panel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic selector for the next AAS truth-producing move."""

    source_pathfinder = pathfinder or load_aas_exponential_value_pathfinder(
        artifact_dir=artifact_dir
    )
    source_activation = activation_board or load_acontext_prerequisite_activation_board(
        artifact_dir=artifact_dir
    )
    source_regret = regret_panel or load_aas_system_integration_flywheel_route_regret_panel(
        artifact_dir=artifact_dir
    )
    _assert_sources_conservative(source_pathfinder, source_activation, source_regret)

    safe_to_claim = _dedupe(
        [
            *source_pathfinder["claim_boundaries"]["safe_to_claim"],
            *source_activation["claim_boundaries"]["safe_to_claim"],
            *source_regret["claim_boundaries"]["safe_to_claim"],
            AAS_EXPONENTIAL_VALUE_PATHFINDER_SAFE_CLAIM,
            ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SAFE_CLAIM,
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM,
            AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_pathfinder["claim_boundaries"]["do_not_claim_yet"],
            *source_activation["claim_boundaries"]["do_not_claim_yet"],
            *source_regret["claim_boundaries"]["do_not_claim_yet"],
            *SELECTOR_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    selector = {
        "schema": AAS_NEXT_TRUTH_SELECTOR_SCHEMA,
        "selector_id": "execution_market.aas.next_truth_selector.2026_05_28_0400",
        "scope": "internal_admin_next_truth_selection_only_no_route_or_customer_promotion",
        "source_artifacts": _source_artifacts(
            source_pathfinder, source_activation, source_regret
        ),
        "derived_from": _derived_from(),
        "access_policy": _access_policy(),
        "readiness": _readiness(),
        "selection_inputs": _selection_inputs(
            source_pathfinder, source_activation, source_regret
        ),
        "truth_track_ranking": _truth_track_ranking(
            source_pathfinder, source_activation, source_regret
        ),
        "selected_next_track": SELECTED_NEXT_TRACK,
        "selected_next_proof": SELECTED_NEXT_PROOF,
        "pattern_to_action_map": _pattern_to_action_map(),
        "blocked_auto_promotions": _blocked_auto_promotions(),
        "operator_next_work_packet": _operator_next_work_packet(source_activation),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "selector_verdict": SELECTOR_VERDICT,
        "operator_instruction": (
            "Use this selector to keep the 4am insight executable: stop adding route "
            "layers, advance the Acontext prerequisite/runtime-truth path, and carry "
            "blocked customer, dispatch, reputation, payment, production, GPS/raw "
            "metadata, authority, and worker-doctrine claims beside every summary."
        ),
    }
    _assert_selector_conservative(selector, source_pathfinder, source_activation, source_regret)
    return selector


def write_aas_next_truth_selector(*, artifact_dir: str | Path | None = None) -> Path:
    """Persist the deterministic next-truth selector fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    selector = build_aas_next_truth_selector(artifact_dir=base_dir)
    path = base_dir / AAS_NEXT_TRUTH_SELECTOR_FILENAME
    path.write_text(json.dumps(selector, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_next_truth_selector(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted next-truth selector fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    selector = json.loads((base_dir / AAS_NEXT_TRUTH_SELECTOR_FILENAME).read_text(encoding="utf-8"))
    pathfinder = load_aas_exponential_value_pathfinder(artifact_dir=base_dir)
    activation = load_acontext_prerequisite_activation_board(artifact_dir=base_dir)
    regret = load_aas_system_integration_flywheel_route_regret_panel(artifact_dir=base_dir)
    _assert_selector_conservative(selector, pathfinder, activation, regret)
    if selector != build_aas_next_truth_selector(
        artifact_dir=base_dir,
        pathfinder=pathfinder,
        activation_board=activation,
        regret_panel=regret,
    ):
        raise CityOpsContractError("AAS next-truth selector drifted from source artifacts")
    return selector


def _source_artifacts(
    pathfinder: dict[str, Any], activation: dict[str, Any], regret: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "file": AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME,
            "schema": pathfinder["schema"],
            "id": pathfinder["pathfinder_id"],
            "digest_sha256": _stable_digest(pathfinder),
        },
        {
            "file": ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME,
            "schema": activation["schema"],
            "id": activation["board_id"],
            "digest_sha256": _stable_digest(activation),
        },
        {
            "file": AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
            "schema": regret["schema"],
            "id": regret["panel_id"],
            "digest_sha256": _stable_digest(regret),
        },
    ]


def _derived_from() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "read_only": True,
        "source_artifacts": [
            AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME,
            ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME,
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
        ],
        "consumes_only": [
            AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME,
            ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME,
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
        ],
        "raw_conversation_reopened": False,
        "raw_worker_evidence_reopened": False,
        "unreviewed_memory_reopened": False,
        "private_operator_context_reopened": False,
        "semantic_reinterpretation_performed": False,
        "starts_acontext_services": False,
        "installs_runtime_dependencies": False,
        "adds_route": False,
        "writes_customer_copy": False,
        "writes_live_acontext": False,
        "retrieves_live_acontext": False,
        "writes_municipal_memory": False,
        "enables_dispatch_automation": False,
        "emits_reputation_receipts": False,
        "reverifies_payment_coverage": False,
        "reverifies_production_infrastructure": False,
        "publishes_worker_doctrine": False,
        "exposes_gps_or_metadata": False,
    }
    return payload


def _access_policy() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "audience": "internal_admin_only",
        "requires_admin_context": True,
    }
    for flag in _FALSE_ACCESS_FLAGS:
        payload[flag] = False
    return payload


def _readiness() -> dict[str, Any]:
    readiness = {
        "selector_landed": True,
        "source_pathfinder_verified": True,
        "source_activation_board_verified": True,
        "source_route_regret_panel_verified": True,
        "selected_track_is_runtime_truth_prerequisite_work": True,
        "selected_track_is_more_route_layering": False,
        "selected_track_is_customer_surface": False,
        "selected_track_is_autonomous_dispatch": False,
    }
    for flag in _FALSE_READINESS_FLAGS:
        readiness[flag] = False
    return readiness


def _selection_inputs(
    pathfinder: dict[str, Any], activation: dict[str, Any], regret: dict[str, Any]
) -> dict[str, Any]:
    return {
        "pathfinder_recommended_proof": pathfinder["recommended_next_proof"]["proof"],
        "pathfinder_may_auto_promote": pathfinder["recommended_next_proof"]["may_auto_promote"],
        "activation_board_verdict": activation["board_verdict"],
        "activation_all_prerequisites_cleared": activation["readiness"]["all_prerequisites_cleared"],
        "activation_ready_to_attempt_live_transport": activation["readiness"][
            "ready_to_attempt_live_transport"
        ],
        "route_regret_verdict": regret["panel_verdict"],
        "route_regret_default_outcome": regret["default_outcome"],
    }


def _truth_track_ranking(
    pathfinder: dict[str, Any], activation: dict[str, Any], regret: dict[str, Any]
) -> list[dict[str, Any]]:
    remaining_actions = [
        action["action"] for action in activation["operator_next_actions"] if action.get("allowed") is True
    ]
    return [
        {
            "rank": 1,
            "track": SELECTED_NEXT_TRACK,
            "selected": True,
            "why": "matches pathfinder rank-1 proof and regret panel runtime-truth escape hatch",
            "source_pathfinder_proof": pathfinder["recommended_next_proof"]["proof"],
            "remaining_prerequisite_actions": remaining_actions,
            "customer_visible": False,
            "may_auto_promote": False,
            "authorizes_live_write": False,
            "authorizes_live_retrieve": False,
            "authorizes_runtime_parity_claim": False,
        },
        {
            "rank": 2,
            "track": "operator_truth_boundary_answer",
            "selected": False,
            "why": "valid future fork from regret panel, but no exact human/operator boundary answer exists in sources",
            "customer_visible": False,
            "may_auto_promote": False,
            "authorizes_customer_delivery": False,
        },
        {
            "rank": 3,
            "track": "documentation_without_new_route_layer",
            "selected": False,
            "why": "allowed only if it references existing artifacts and preserves blocked claims; lower multiplier than runtime truth",
            "customer_visible": False,
            "may_auto_promote": False,
            "authorizes_publication": False,
        },
        {
            "rank": 4,
            "track": "more_internal_route_layering",
            "selected": False,
            "why": "explicitly regretted by source panel because it adds ceremony rather than truth",
            "customer_visible": False,
            "may_auto_promote": False,
            "authorizes_new_route": False,
        },
    ]


def _pattern_to_action_map() -> list[dict[str, Any]]:
    return [
        {
            "pattern": "memory_system_data_compounds_only_after_reviewed_transport",
            "action": "clear_acontext_prerequisites_before_any_memory_sink_claim",
            "forbidden_shortcut": "raw_memory_or_transcript_direct_to_live_acontext",
        },
        {
            "pattern": "irc_coordination_scales_by_four_ids_not_context_bulk",
            "action": "carry_four_source_artifact_ids_and_claim_boundaries_instead_of_new_route_layers",
            "forbidden_shortcut": "change_runtime_session_manager_from_strategy_artifact",
        },
        {
            "pattern": "cross_project_intelligence_is_filter_not_autopilot",
            "action": "convert insights into one proof gate plus explicit quarantines",
            "forbidden_shortcut": "resume_stopped_projects_or_autoroute_customer_work",
        },
        {
            "pattern": "agent_coordination_quality_is_private_until_separately_approved",
            "action": "score proof discipline internally before any reputation_or_worker_skill_dna_surface",
            "forbidden_shortcut": "publish_coordination_scores_as_erc8004_reputation",
        },
    ]


def _blocked_auto_promotions() -> list[dict[str, str]]:
    return [
        {
            "temptation": "breakthrough_pattern_means_live_runtime_ready",
            "blocked_by": "next_truth_selector_authorizes_live_acontext_write_or_retrieve",
        },
        {
            "temptation": "route_regret_panel_means_operator_queue_ready",
            "blocked_by": "next_truth_selector_authorizes_queue_launch_or_dispatch",
        },
        {
            "temptation": "private_coordination_quality_means_public_reputation_ready",
            "blocked_by": "next_truth_selector_authorizes_erc8004_reputation_or_worker_skill_dna",
        },
        {
            "temptation": "portfolio_pattern_map_means_customer_packaging_ready",
            "blocked_by": "next_truth_selector_authorizes_customer_copy_or_delivery",
        },
    ]


def _operator_next_work_packet(activation: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_type": "internal_admin_runtime_truth_prerequisite_packet",
        "selected_track": SELECTED_NEXT_TRACK,
        "selected_next_proof": SELECTED_NEXT_PROOF,
        "allowed_now": [
            "complete_local_acontext_service_startup",
            "wire_active_runner_to_acontext_sdk",
            "rerun_read_only_preflight_after_prerequisites_clear",
        ],
        "source_activation_actions": activation["operator_next_actions"],
        "must_rebuild_before_live_attempt": [
            "acontext_live_preflight_blocker_delta",
            "acontext_live_preflight_blocker_delta_read_surface",
            "acontext_live_parity_attempt_readiness_gate",
        ],
        "live_write_or_retrieve_allowed_now": False,
        "customer_or_worker_surface_allowed_now": False,
    }


def _assert_sources_conservative(
    pathfinder: dict[str, Any], activation: dict[str, Any], regret: dict[str, Any]
) -> None:
    if pathfinder.get("schema") != AAS_EXPONENTIAL_VALUE_PATHFINDER_SCHEMA:
        raise CityOpsContractError("AAS next-truth selector requires exponential-value pathfinder source")
    if activation.get("schema") != ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SCHEMA:
        raise CityOpsContractError("AAS next-truth selector requires Acontext activation board source")
    if regret.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SCHEMA:
        raise CityOpsContractError("AAS next-truth selector requires route regret panel source")
    if pathfinder.get("recommended_next_proof", {}).get("may_auto_promote") is not False:
        raise CityOpsContractError("AAS next-truth selector refuses promoted pathfinder proof")
    if pathfinder.get("recommended_next_proof", {}).get("customer_visible") is not False:
        raise CityOpsContractError("AAS next-truth selector refuses customer-visible pathfinder proof")
    activation_readiness = activation.get("readiness") or {}
    for flag in [
        "ready_to_attempt_live_transport",
        "attempt_allowed",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "runtime_parity_proven",
    ]:
        if activation_readiness.get(flag) is not False:
            raise CityOpsContractError(f"AAS next-truth selector refuses promoted activation board: {flag}")
    regret_readiness = regret.get("readiness") or {}
    if regret.get("panel_verdict") != REGRET_PANEL_VERDICT:
        raise CityOpsContractError("AAS next-truth selector requires stop-route verdict")
    if regret.get("default_outcome") != REGRET_PANEL_DEFAULT_OUTCOME:
        raise CityOpsContractError("AAS next-truth selector requires route regret default outcome")
    for flag in [
        "new_route_requested",
        "runtime_truth_present",
        "operator_truth_present",
        "customer_delivery_ready",
        "dispatch_ready",
        "live_acontext_runtime_parity_ready",
    ]:
        if regret_readiness.get(flag) is not False:
            raise CityOpsContractError(f"AAS next-truth selector refuses promoted regret panel: {flag}")
    for source in [pathfinder, activation, regret]:
        _assert_claim_boundaries(
            source["claim_boundaries"]["safe_to_claim"],
            source["claim_boundaries"]["do_not_claim_yet"],
        )


def _assert_selector_conservative(
    selector: dict[str, Any],
    pathfinder: dict[str, Any],
    activation: dict[str, Any],
    regret: dict[str, Any],
) -> None:
    _assert_sources_conservative(pathfinder, activation, regret)
    if selector.get("schema") != AAS_NEXT_TRUTH_SELECTOR_SCHEMA:
        raise CityOpsContractError("AAS next-truth selector schema drift")
    if selector.get("selector_verdict") != SELECTOR_VERDICT:
        raise CityOpsContractError("AAS next-truth selector verdict drift")
    if selector.get("selected_next_track") != SELECTED_NEXT_TRACK:
        raise CityOpsContractError("AAS next-truth selector selected track drift")
    if selector.get("selected_next_proof") != SELECTED_NEXT_PROOF:
        raise CityOpsContractError("AAS next-truth selector selected proof drift")
    derived = selector.get("derived_from") or {}
    if derived.get("consumes_only") != [
        AAS_EXPONENTIAL_VALUE_PATHFINDER_FILENAME,
        ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME,
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
    ]:
        raise CityOpsContractError("AAS next-truth selector source list drift")
    for flag, expected in {
        "read_only": True,
        "raw_conversation_reopened": False,
        "raw_worker_evidence_reopened": False,
        "unreviewed_memory_reopened": False,
        "private_operator_context_reopened": False,
        "semantic_reinterpretation_performed": False,
        "starts_acontext_services": False,
        "installs_runtime_dependencies": False,
        "adds_route": False,
        "writes_customer_copy": False,
        "writes_live_acontext": False,
        "retrieves_live_acontext": False,
        "enables_dispatch_automation": False,
        "emits_reputation_receipts": False,
        "reverifies_payment_coverage": False,
        "reverifies_production_infrastructure": False,
        "publishes_worker_doctrine": False,
        "exposes_gps_or_metadata": False,
    }.items():
        if derived.get(flag) is not expected:
            raise CityOpsContractError(f"AAS next-truth selector derived drift: {flag}")
    access = selector.get("access_policy") or {}
    if access.get("audience") != "internal_admin_only":
        raise CityOpsContractError("AAS next-truth selector audience drift")
    if access.get("requires_admin_context") is not True:
        raise CityOpsContractError("AAS next-truth selector requires admin context")
    for flag in _FALSE_ACCESS_FLAGS:
        if access.get(flag) is not False:
            raise CityOpsContractError(f"AAS next-truth selector access promoted: {flag}")
    readiness = selector.get("readiness") or {}
    if readiness.get("selector_landed") is not True:
        raise CityOpsContractError("AAS next-truth selector landed flag missing")
    if readiness.get("selected_track_is_runtime_truth_prerequisite_work") is not True:
        raise CityOpsContractError("AAS next-truth selector must choose runtime prerequisite work")
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"AAS next-truth selector readiness promoted: {flag}")
    rankings = selector.get("truth_track_ranking") or []
    if [track.get("rank") for track in rankings] != [1, 2, 3, 4]:
        raise CityOpsContractError("AAS next-truth selector ranking order drift")
    if rankings[0].get("track") != SELECTED_NEXT_TRACK or rankings[0].get("selected") is not True:
        raise CityOpsContractError("AAS next-truth selector must rank runtime prerequisite work first")
    for row in rankings:
        if row.get("customer_visible") is not False:
            raise CityOpsContractError("AAS next-truth selector ranking promoted customer visibility")
        if row.get("may_auto_promote") is not False:
            raise CityOpsContractError("AAS next-truth selector ranking promoted readiness")
        for key, value in row.items():
            if key.startswith("authorizes_") and value is not False:
                raise CityOpsContractError("AAS next-truth selector ranking promoted authorization")
    packet = selector.get("operator_next_work_packet") or {}
    if packet.get("live_write_or_retrieve_allowed_now") is not False:
        raise CityOpsContractError("AAS next-truth selector packet allowed live Acontext")
    if packet.get("customer_or_worker_surface_allowed_now") is not False:
        raise CityOpsContractError("AAS next-truth selector packet allowed customer/worker surface")
    safe = selector.get("claim_boundaries", {}).get("safe_to_claim", [])
    blocked = selector.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    _assert_claim_boundaries(safe, blocked)
    if AAS_NEXT_TRUTH_SELECTOR_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS next-truth selector safe claim missing")
    missing = sorted(set(SELECTOR_BLOCKED_CLAIMS) - set(blocked))
    if missing:
        raise CityOpsContractError(f"AAS next-truth selector missing blocked claims: {missing}")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"AAS next-truth selector claim overlap: {overlap}")


def _stable_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
