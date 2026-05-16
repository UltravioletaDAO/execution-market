"""Internal activation board for clearing Acontext live-parity prerequisites.

The parity-attempt gate says the live Acontext write/retrieve run is blocked by
missing SDK/API/dashboard prerequisites.  This module records the next smallest
safe setup surface: what activation assets exist locally, what still must be
wired, and which claims remain blocked.

It never writes to Acontext, never retrieves from Acontext, never starts a
customer/public route, and never promotes runtime, dispatch, reputation,
payment, production, GPS/raw metadata, or worker-doctrine readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_live_parity_attempt_readiness_gate import (
    ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME,
    ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SAFE_CLAIM,
    ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SCHEMA,
    GATE_BLOCKED_CLAIMS,
    load_acontext_live_parity_attempt_readiness_gate,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SCHEMA = (
    "city_ops.acontext_prerequisite_activation_board.v1"
)
ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME = (
    "acontext_prerequisite_activation_board.json"
)
ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SAFE_CLAIM = (
    "admin_acontext_prerequisite_activation_board_landed"
)

ACTIVATION_BOARD_BLOCKED_CLAIMS = [
    *GATE_BLOCKED_CLAIMS,
    "acontext_cli_installation_authorizes_live_attempt",
    "acontext_compose_manifest_authorizes_live_attempt",
    "acontext_dedicated_sdk_venv_authorizes_active_runner",
    "acontext_api_dashboard_started_by_board",
    "acontext_prerequisites_fully_cleared_by_activation_board",
    "acontext_preflight_rerun_completed_by_activation_board",
    "acontext_live_parity_attempt_authorized_by_activation_board",
    "acontext_live_write_completed_by_activation_board",
    "acontext_live_retrieval_completed_by_activation_board",
    "acontext_sink_ready_by_activation_board",
    "runtime_parity_proven_by_activation_board",
]

_FALSE_ACCESS_FLAGS = [
    "network_route_registered",
    "public_route_registered",
    "customer_visible",
    "worker_visible",
    "dispatch_enabled",
    "writes_live_acontext",
    "retrieves_live_acontext",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_READINESS_FLAGS = [
    "ready_to_attempt_live_transport",
    "attempt_allowed",
    "all_prerequisites_cleared",
    "preflight_rerun_completed",
    "live_acontext_write_performed",
    "live_acontext_retrieval_performed",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "live_memory_transport_swap_ready",
    "customer_visible_aas_packaging_ready",
    "public_route_ready",
    "operator_queue_launch_ready",
    "autonomous_dispatch_ready",
    "erc8004_reputation_ready",
    "payment_coverage_reverified_by_this_board",
    "production_infrastructure_reverified_by_this_board",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_doctrine_ready",
]


def build_may16_midnight_activation_observation() -> dict[str, Any]:
    """Return the deterministic midnight activation observation for fixtures."""

    return {
        "docker_available": True,
        "acontext_cli_installed": True,
        "compose_manifest_found": True,
        "compose_start_attempted": True,
        "compose_start_completed": False,
        "dedicated_sdk_venv_found": True,
        "active_runner_sdk_available": False,
        "active_runner_sdk_install_attempted": True,
        "active_runner_sdk_install_succeeded": False,
        "active_runner_sdk_install_blocker": "homebrew_python_pyexpat_linkage_error",
        "local_acontext_api_reachable": False,
        "local_acontext_dashboard_reachable": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
    }


def build_acontext_prerequisite_activation_board(
    *,
    artifact_dir: str | Path | None = None,
    gate: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed board for prerequisite activation work."""

    source_gate = gate or load_acontext_live_parity_attempt_readiness_gate(
        artifact_dir=artifact_dir
    )
    observed = observation or build_may16_midnight_activation_observation()
    _assert_source_gate(source_gate)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source_gate["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SAFE_CLAIM,
            ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_gate["claim_boundaries"]["do_not_claim_yet"],
            *ACTIVATION_BOARD_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    board = {
        "schema": ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SCHEMA,
        "board_id": f"acontext_prerequisite_activation_board:{source_gate['gate_id']}",
        "source_gate_id": source_gate["gate_id"],
        "source_delta_id": source_gate["source_delta_id"],
        "source_preflight_id": source_gate["source_preflight_id"],
        "proof_anchor_id": source_gate["proof_anchor_id"],
        "coordination_session_id": source_gate["coordination_session_id"],
        "compact_decision_id": source_gate["compact_decision_id"],
        "review_packet_id": source_gate["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME],
            "consumes_only": [ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_FILENAME],
            "forbidden_inputs": [
                "raw_transcripts",
                "unreviewed_memory",
                "private_operator_context",
                "freeform_worker_chat",
                "live_acontext_sink_writes",
                "live_acontext_retrievals",
                "payment_processor_probe",
                "production_health_probe",
                "gps_or_raw_metadata_payloads",
                "customer_copy_drafts",
                "worker_instruction_templates",
            ],
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "starts_acontext_services": False,
            "installs_runtime_dependencies": False,
            "semantic_reinterpretation_performed": False,
            "reverifies_payment_coverage": False,
            "reverifies_production_infrastructure": False,
            "writes_customer_copy": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            "network_route_registered": False,
            "public_route_registered": False,
            "customer_visible": False,
            "worker_visible": False,
            "dispatch_enabled": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "emits_reputation_receipts": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "activation_observation": dict(observed),
        "activation_cards": _activation_cards(observed),
        "readiness": _activation_readiness(observed),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_next_actions": _operator_next_actions(observed),
        "board_verdict": _board_verdict(observed),
        "operator_instruction": (
            "Treat this as setup progress only. Finish service startup and active-runner "
            "SDK wiring, rerun the read-only preflight, rebuild the blocker delta/read "
            "surface/gate, and only then consider one live write/retrieve parity attempt."
        ),
    }
    _assert_board_conservative(board)
    return board


def write_acontext_prerequisite_activation_board(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Acontext prerequisite activation board."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    board = build_acontext_prerequisite_activation_board(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME
    path.write_text(json.dumps(board, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_prerequisite_activation_board(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted activation board."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        board = json.load(fh)
    _assert_board_conservative(board)
    return board


def _activation_cards(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": "local_runtime_assets",
            "status": "partial_assets_present",
            "docker_available": observed["docker_available"],
            "acontext_cli_installed": observed["acontext_cli_installed"],
            "compose_manifest_found": observed["compose_manifest_found"],
            "dedicated_sdk_venv_found": observed["dedicated_sdk_venv_found"],
            "active_runner_sdk_available": observed["active_runner_sdk_available"],
        },
        {
            "card": "service_startup",
            "status": "not_yet_reachable",
            "compose_start_attempted": observed["compose_start_attempted"],
            "compose_start_completed": observed["compose_start_completed"],
            "local_acontext_api_reachable": observed["local_acontext_api_reachable"],
            "local_acontext_dashboard_reachable": observed[
                "local_acontext_dashboard_reachable"
            ],
        },
        {
            "card": "active_runner_sdk_gap",
            "status": "dedicated_venv_present_but_test_runner_missing_sdk",
            "dedicated_sdk_venv_found": observed["dedicated_sdk_venv_found"],
            "active_runner_sdk_install_attempted": observed[
                "active_runner_sdk_install_attempted"
            ],
            "active_runner_sdk_install_succeeded": observed[
                "active_runner_sdk_install_succeeded"
            ],
            "active_runner_sdk_install_blocker": observed[
                "active_runner_sdk_install_blocker"
            ],
        },
        {
            "card": "claim_boundary",
            "status": "setup_progress_does_not_authorize_live_parity",
            "authorizes_live_write": False,
            "authorizes_live_retrieve": False,
            "authorizes_runtime_parity_claim": False,
            "authorizes_customer_or_worker_surface": False,
        },
    ]


def _activation_readiness(observed: dict[str, Any]) -> dict[str, Any]:
    all_prereqs = all(
        [
            observed["docker_available"],
            observed["acontext_cli_installed"],
            observed["compose_manifest_found"],
            observed["active_runner_sdk_available"],
            observed["local_acontext_api_reachable"],
            observed["local_acontext_dashboard_reachable"],
        ]
    )
    return {
        "activation_board_landed": True,
        "docker_available": observed["docker_available"],
        "acontext_cli_installed": observed["acontext_cli_installed"],
        "compose_manifest_found": observed["compose_manifest_found"],
        "dedicated_sdk_venv_found": observed["dedicated_sdk_venv_found"],
        "active_runner_sdk_available": observed["active_runner_sdk_available"],
        "local_acontext_api_reachable": observed["local_acontext_api_reachable"],
        "local_acontext_dashboard_reachable": observed[
            "local_acontext_dashboard_reachable"
        ],
        "all_prerequisites_cleared": all_prereqs,
        "ready_to_rerun_preflight_with_all_prereqs": all_prereqs,
        "preflight_rerun_completed": False,
        "ready_to_attempt_live_transport": False,
        "attempt_allowed": False,
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "acontext_sink_ready": False,
        "runtime_parity_proven": False,
        "live_memory_transport_swap_ready": False,
        "customer_visible_aas_packaging_ready": False,
        "public_route_ready": False,
        "operator_queue_launch_ready": False,
        "autonomous_dispatch_ready": False,
        "erc8004_reputation_ready": False,
        "payment_coverage_reverified_by_this_board": False,
        "production_infrastructure_reverified_by_this_board": False,
        "gps_or_metadata_exposure_allowed": False,
        "worker_copyable_doctrine_ready": False,
    }


def _operator_next_actions(observed: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not observed["local_acontext_api_reachable"] or not observed[
        "local_acontext_dashboard_reachable"
    ]:
        actions.append(
            {
                "action": "complete_local_acontext_service_startup",
                "allowed": True,
                "live_write_or_retrieve_allowed": False,
                "success_condition": "API and dashboard answer read-only health probes",
            }
        )
    if not observed["active_runner_sdk_available"]:
        actions.append(
            {
                "action": "wire_active_runner_to_acontext_sdk",
                "allowed": True,
                "live_write_or_retrieve_allowed": False,
                "success_condition": "the Python runtime used by the preflight can import acontext",
            }
        )
    actions.append(
        {
            "action": "rerun_read_only_preflight_and_rebuild_gate",
            "allowed_after_prerequisites_clear": True,
            "live_write_or_retrieve_allowed": False,
            "success_condition": "new gate explicitly authorizes exactly one parity attempt",
        }
    )
    return actions


def _board_verdict(observed: dict[str, Any]) -> str:
    readiness = _activation_readiness(observed)
    if readiness["all_prerequisites_cleared"]:
        return "activation_assets_present_but_preflight_rerun_still_required"
    return "activation_started_not_live_ready"


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if gate.get("schema") != ACONTEXT_LIVE_PARITY_ATTEMPT_READINESS_GATE_SCHEMA:
        raise CityOpsContractError("Acontext activation board requires parity gate source")
    readiness = gate.get("readiness") or {}
    if readiness.get("attempt_allowed") is not False:
        raise CityOpsContractError("Acontext activation board cannot consume allowed gate")
    if readiness.get("ready_to_attempt_live_transport") is not False:
        raise CityOpsContractError("Acontext activation board cannot consume ready gate")
    if readiness.get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("Acontext activation board cannot consume live write")
    if readiness.get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("Acontext activation board cannot consume live retrieval")


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    required = {
        "docker_available",
        "acontext_cli_installed",
        "compose_manifest_found",
        "compose_start_attempted",
        "compose_start_completed",
        "dedicated_sdk_venv_found",
        "active_runner_sdk_available",
        "active_runner_sdk_install_attempted",
        "active_runner_sdk_install_succeeded",
        "active_runner_sdk_install_blocker",
        "local_acontext_api_reachable",
        "local_acontext_dashboard_reachable",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
    }
    missing = required - set(observed)
    if missing:
        raise CityOpsContractError(
            f"Acontext activation observation missing fields: {sorted(missing)}"
        )
    if observed["live_acontext_write_performed"]:
        raise CityOpsContractError("Acontext activation board cannot record live write")
    if observed["live_acontext_retrieval_performed"]:
        raise CityOpsContractError("Acontext activation board cannot record live retrieval")


def _assert_claim_boundaries(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"Acontext activation board has blocked safe claims: {sorted(overlap)}"
        )


def _assert_board_conservative(board: dict[str, Any]) -> None:
    if board.get("schema") != ACONTEXT_PREREQUISITE_ACTIVATION_BOARD_SCHEMA:
        raise CityOpsContractError("Unexpected Acontext activation board schema")
    for flag in _FALSE_ACCESS_FLAGS:
        if board.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"Acontext activation board promoted access: {flag}")
    readiness = board.get("readiness") or {}
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"Acontext activation board promoted readiness: {flag}")
    blocked = set(board.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    safe = set(board.get("claim_boundaries", {}).get("safe_to_claim", []))
    if safe & blocked:
        raise CityOpsContractError(
            f"Acontext activation board has blocked safe claims: {sorted(safe & blocked)}"
        )
    if not set(ACTIVATION_BOARD_BLOCKED_CLAIMS) <= blocked:
        raise CityOpsContractError("Acontext activation board dropped blocked claims")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
