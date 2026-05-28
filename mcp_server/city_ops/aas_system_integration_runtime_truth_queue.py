"""Internal/admin runtime-truth queue for AAS system integration.

This module consumes the route regret panel and the latest daemon-down Acontext
recheck, then names the only safe runtime path forward. It is a planning queue,
not a runtime attempt: it starts no Docker services, writes no live Acontext
memory, retrieves no live Acontext data, creates no customer/public route,
enables no dispatch, emits no reputation receipt, does not reverify payment or
production, and exposes no GPS/raw metadata or worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_system_integration_flywheel_route_regret_panel import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SCHEMA,
    REGRET_PANEL_BLOCKED_CLAIMS,
    REGRET_PANEL_READINESS_FLAGS,
    build_aas_system_integration_flywheel_route_regret_panel,
    load_aas_system_integration_flywheel_route_regret_panel,
)
from .acontext_runtime_memory_daemon_recheck import (
    ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME,
    ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM,
    ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SCHEMA,
    DAEMON_RECHECK_BLOCKED_CLAIMS,
    build_acontext_runtime_memory_daemon_recheck,
    load_acontext_runtime_memory_daemon_recheck,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SCHEMA = (
    "city_ops.aas_system_integration_runtime_truth_queue.v1"
)
AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_FILENAME = (
    "aas_system_integration_runtime_truth_queue.json"
)
AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SAFE_CLAIM = (
    "internal_admin_aas_system_integration_runtime_truth_queue_landed"
)

RUNTIME_TRUTH_QUEUE_ID = (
    "execution_market.aas.system_integration.runtime_truth_queue.2026_05_28_0300"
)
RUNTIME_TRUTH_QUEUE_SCOPE = (
    "internal_admin_runtime_truth_queue_only_no_live_parity_attempt"
)
RUNTIME_TRUTH_QUEUE_VERDICT = (
    "runtime_truth_queue_ready_but_live_parity_blocked_by_daemon_prerequisites"
)

RUNTIME_TRUTH_QUEUE_BLOCKED_CLAIMS = [
    *REGRET_PANEL_BLOCKED_CLAIMS,
    *DAEMON_RECHECK_BLOCKED_CLAIMS,
    "runtime_truth_queue_started_docker_or_compose",
    "runtime_truth_queue_repaired_docker_socket",
    "runtime_truth_queue_pulled_or_cached_images",
    "runtime_truth_queue_reached_live_acontext_api_or_dashboard",
    "runtime_truth_queue_rebuilt_empty_readiness_gate",
    "runtime_truth_queue_authorized_live_write_retrieve_attempt",
    "runtime_truth_queue_completed_live_acontext_write",
    "runtime_truth_queue_completed_live_acontext_retrieval",
    "runtime_truth_queue_proved_memory_acontext_parity",
    "runtime_truth_queue_changes_irc_runtime_session_manager",
    "runtime_truth_queue_enables_cross_project_autorouting",
    "runtime_truth_queue_is_customer_or_public_surface",
    "runtime_truth_queue_authorizes_customer_copy_delivery_or_publication",
    "runtime_truth_queue_registers_catalog_or_public_route",
    "runtime_truth_queue_authorizes_pricing_or_customer_quote",
    "runtime_truth_queue_authorizes_queue_launch_or_dispatch",
    "runtime_truth_queue_authorizes_erc8004_reputation_or_worker_skill_dna",
    "runtime_truth_queue_reverifies_payment_or_production",
    "runtime_truth_queue_allows_exact_gps_or_raw_metadata",
    "runtime_truth_queue_grants_domain_authority",
    "runtime_truth_queue_creates_worker_copyable_doctrine",
]

RUNTIME_TRUTH_QUEUE_FALSE_ACCESS_FLAGS = {
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "operator_queue_launched": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "writes_municipal_memory": False,
    "changes_irc_runtime_session_manager": False,
    "enables_cross_project_autorouting": False,
    "emits_reputation_receipts": False,
    "exposes_gps_or_metadata": False,
    "publishes_worker_doctrine": False,
}

RUNTIME_TRUTH_QUEUE_READINESS_FLAGS = {
    "runtime_truth_queue_landed": True,
    "source_regret_panel_verified": True,
    "source_daemon_recheck_verified": True,
    "route_layering_stopped": True,
    "runtime_truth_path_named": True,
    "docker_daemon_available": False,
    "buildx_builder_available": False,
    "required_image_inventory_checked": False,
    "required_images_present": False,
    "compose_services_started": False,
    "acontext_api_reachable": False,
    "acontext_dashboard_reachable": False,
    "readiness_gate_rebuilt_empty": False,
    "one_live_parity_attempt_authorized": False,
    "live_acontext_write_performed": False,
    "live_acontext_retrieval_performed": False,
    "memory_acontext_parity_ready": False,
    "irc_runtime_session_manager_enhanced": False,
    "cross_project_autorouting_ready": False,
    "agent_observability_live_dashboard_ready": False,
    "customer_copy_ready": False,
    "customer_delivery_ready": False,
    "publication_ready": False,
    "public_or_catalog_route_ready": False,
    "pricing_or_customer_quote_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_ready": False,
    "payment_or_production_reverified": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "exact_gps_or_raw_metadata_release_ready": False,
    "domain_authority_ready": False,
    "worker_copyable_doctrine_ready": False,
}


def build_aas_system_integration_runtime_truth_queue(
    *,
    artifact_dir: str | Path | None = None,
    regret_panel: dict[str, Any] | None = None,
    daemon_recheck: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin runtime-truth queue."""

    panel = regret_panel or load_or_build_route_regret_panel(artifact_dir=artifact_dir)
    recheck = daemon_recheck or load_or_build_daemon_recheck(artifact_dir=artifact_dir)
    _assert_regret_panel_source(panel)
    _assert_daemon_recheck_source(recheck)

    safe_to_claim = _dedupe(
        [
            *panel["claim_boundaries"]["safe_to_claim"],
            *recheck["claim_boundaries"]["safe_to_claim"],
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM,
            ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM,
            AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *panel["claim_boundaries"]["do_not_claim_yet"],
            *recheck["claim_boundaries"]["do_not_claim_yet"],
            *RUNTIME_TRUTH_QUEUE_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    queue = {
        "schema": AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SCHEMA,
        "queue_id": RUNTIME_TRUTH_QUEUE_ID,
        "scope": RUNTIME_TRUTH_QUEUE_SCOPE,
        "source_artifacts": {
            "route_regret_panel": {
                "file": AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
                "schema": panel["schema"],
                "id": panel["panel_id"],
                "safe_claim": AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM,
                "digest_sha256": _stable_digest(panel),
                "panel_verdict": panel["panel_verdict"],
            },
            "acontext_daemon_recheck": {
                "file": ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME,
                "schema": recheck["schema"],
                "id": recheck["recheck_id"],
                "safe_claim": ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM,
                "digest_sha256": _stable_digest(recheck),
                "recheck_verdict": recheck["recheck_verdict"],
            },
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
                ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME,
            ],
            "consumes_only": [
                AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME,
                ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME,
            ],
            "raw_conversation_reopened": False,
            "raw_worker_evidence_reopened": False,
            "unreviewed_memory_reopened": False,
            "private_operator_context_reopened": False,
            "starts_docker_desktop": False,
            "pulls_container_images": False,
            "starts_compose_services": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "changes_irc_runtime_session_manager": False,
            "enables_cross_project_autorouting": False,
            "writes_customer_copy": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "reverifies_payment_coverage": False,
            "reverifies_production_infrastructure": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **RUNTIME_TRUTH_QUEUE_FALSE_ACCESS_FLAGS,
        },
        "runtime_truth_gates": _runtime_truth_gates(recheck),
        "coordination_connection_cards": _coordination_connection_cards(panel, recheck),
        "success_metric_cards": _success_metric_cards(),
        "allowed_next_actions": [
            "Repair or start the local Docker daemon/socket outside this artifact, then record a new prerequisite observation.",
            "Only after Docker and image inventory are green, start Compose and verify local Acontext API/dashboard health in a separate artifact.",
            "Only after an empty readiness gate is rebuilt, authorize exactly one bounded live write/retrieve parity attempt.",
        ],
        "forbidden_next_actions": [
            "Do not add more internal route layers as a substitute for runtime truth.",
            "Do not claim memory-to-Acontext parity until a live write and retrieval are both recorded.",
            "Do not change IRC runtime session management or cross-project autorouting from this planning queue.",
            "Do not create customer copy, delivery, publication, pricing, dispatch, reputation, Worker Skill DNA, GPS/raw metadata release, authority claims, or worker-copyable doctrine from this queue.",
        ],
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": dict(RUNTIME_TRUTH_QUEUE_READINESS_FLAGS),
        "claim_boundary_footer": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
            "safe_claim_count": len(safe_to_claim),
            "blocked_claim_count": len(do_not_claim_yet),
        },
        "queue_verdict": RUNTIME_TRUTH_QUEUE_VERDICT,
    }
    _assert_runtime_truth_queue_contract(queue, panel, recheck)
    return queue


def load_or_build_route_regret_panel(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted route regret panel or rebuild it deterministically."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_FILENAME
    if path.exists():
        panel = load_aas_system_integration_flywheel_route_regret_panel(
            artifact_dir=base_dir
        )
    else:
        panel = build_aas_system_integration_flywheel_route_regret_panel(
            artifact_dir=base_dir
        )
    _assert_regret_panel_source(panel)
    return panel


def load_or_build_daemon_recheck(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted Acontext daemon recheck or rebuild it deterministically."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_FILENAME
    if path.exists():
        recheck = load_acontext_runtime_memory_daemon_recheck(artifact_dir=base_dir)
    else:
        recheck = build_acontext_runtime_memory_daemon_recheck(artifact_dir=base_dir)
    _assert_daemon_recheck_source(recheck)
    return recheck


def load_aas_system_integration_runtime_truth_queue(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted runtime-truth queue fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_FILENAME
    queue = json.loads(path.read_text(encoding="utf-8"))
    panel = load_or_build_route_regret_panel(artifact_dir=base_dir)
    recheck = load_or_build_daemon_recheck(artifact_dir=base_dir)
    _assert_runtime_truth_queue_contract(queue, panel, recheck)
    return queue


def write_aas_system_integration_runtime_truth_queue(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic runtime-truth queue fixture."""

    queue = build_aas_system_integration_runtime_truth_queue(artifact_dir=artifact_dir)
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_FILENAME
    path.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _runtime_truth_gates(recheck: dict[str, Any]) -> list[dict[str, Any]]:
    summary = recheck["daemon_status_summary"]
    return [
        {
            "gate": "docker_daemon_socket",
            "status": "blocked",
            "current_signal": summary["docker_context"],
            "passed": False,
            "required_before_next": "docker_daemon_available_true_and_buildx_builder_healthy",
            "authorizes_live_attempt": False,
        },
        {
            "gate": "required_image_inventory",
            "status": "blocked_by_daemon_unavailable",
            "passed": False,
            "required_before_next": "complete_required_acontext_image_inventory_checked_and_present",
            "authorizes_live_attempt": False,
        },
        {
            "gate": "local_acontext_services",
            "status": "blocked_by_no_compose_start",
            "passed": False,
            "required_before_next": "api_and_dashboard_reachable_on_localhost",
            "authorizes_live_attempt": False,
        },
        {
            "gate": "empty_readiness_gate",
            "status": "blocked_until_services_reachable",
            "passed": False,
            "required_before_next": "readiness_gate_rebuilt_with_empty_blockers",
            "authorizes_live_attempt": False,
        },
        {
            "gate": "single_live_write_retrieve_parity_attempt",
            "status": "not_authorized",
            "passed": False,
            "required_before_next": "all_prior_runtime_gates_passed_in_order",
            "authorizes_live_attempt": False,
        },
    ]


def _coordination_connection_cards(
    panel: dict[str, Any], recheck: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "connection": "memory_system_to_acontext",
            "current_truth": recheck["recheck_verdict"],
            "safe_now": "plan_the_order_only",
            "blocked_until": "live_write_and_retrieval_are_recorded_after_prerequisite_gate",
            "creates_runtime_change": False,
        },
        {
            "connection": "irc_session_management",
            "current_truth": panel["panel_verdict"],
            "safe_now": "preserve_four_id_handoff_discipline_as_design_input",
            "blocked_until": "separate_runtime_session_manager_change_request_and_tests",
            "creates_runtime_change": False,
        },
        {
            "connection": "cross_project_decision_support",
            "current_truth": "priority_firewall_prevents_stopped_work_from_becoming_runtime_scope",
            "safe_now": "use_stop_list_as_a_decision_support_signal_for_aas_only",
            "blocked_until": "operator_authorizes_specific_external_project_scope",
            "creates_runtime_change": False,
        },
        {
            "connection": "agent_observability_success_metrics",
            "current_truth": "success_is_restraint_plus_verified_gate_order",
            "safe_now": "track_gate_order_and_blocked_claims_as_success_metrics",
            "blocked_until": "separate_live_observability_surface_is_built",
            "creates_runtime_change": False,
        },
    ]


def _success_metric_cards() -> list[dict[str, Any]]:
    return [
        {
            "metric": "route_layer_regret_respected",
            "target": "no_new_route_layers_without_runtime_or_operator_truth",
            "status": "green",
        },
        {
            "metric": "runtime_gate_order_preserved",
            "target": "docker_then_images_then_services_then_empty_gate_then_single_parity_attempt",
            "status": "planned_not_executed",
        },
        {
            "metric": "blocked_claims_kept_adjacent",
            "target": "every safe claim ships with its explicit do_not_claim_yet list",
            "status": "green",
        },
        {
            "metric": "external_scope_firewall_honored",
            "target": "no AutoJob Frontier KK or KarmaCadabra dream work",
            "status": "green",
        },
    ]


def _assert_regret_panel_source(panel: dict[str, Any]) -> None:
    if panel.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SCHEMA:
        raise CityOpsContractError("invalid route regret panel schema")
    if AAS_SYSTEM_INTEGRATION_FLYWHEEL_ROUTE_REGRET_PANEL_SAFE_CLAIM not in panel.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("route regret panel missing safe claim")
    if panel.get("panel_verdict") != "stop_internal_route_layering_until_runtime_or_operator_truth_exists":
        raise CityOpsContractError("route regret panel verdict drift")
    for flag, expected in REGRET_PANEL_READINESS_FLAGS.items():
        if panel.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"route regret panel readiness drift: {flag}")
    _assert_no_claim_overlap(
        panel.get("claim_boundaries", {}).get("safe_to_claim", []),
        panel.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_daemon_recheck_source(recheck: dict[str, Any]) -> None:
    if recheck.get("schema") != ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SCHEMA:
        raise CityOpsContractError("invalid Acontext daemon recheck schema")
    if ACONTEXT_RUNTIME_MEMORY_DAEMON_RECHECK_SAFE_CLAIM not in recheck.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext daemon recheck missing safe claim")
    readiness = recheck.get("readiness", {})
    for flag in [
        "docker_daemon_available",
        "buildx_builder_available",
        "required_images_present",
        "compose_services_started",
        "api_reachable_after_recheck",
        "dashboard_reachable_after_recheck",
        "readiness_gate_rebuilt_with_empty_blockers",
        "one_live_parity_attempt_authorized",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "runtime_parity_proven",
    ]:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"Acontext daemon recheck readiness promoted: {flag}")
    _assert_no_claim_overlap(
        recheck.get("claim_boundaries", {}).get("safe_to_claim", []),
        recheck.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_runtime_truth_queue_contract(
    queue: dict[str, Any], panel: dict[str, Any], recheck: dict[str, Any]
) -> None:
    if queue.get("schema") != AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SCHEMA:
        raise CityOpsContractError("invalid runtime truth queue schema")
    sources = queue.get("source_artifacts", {})
    if sources.get("route_regret_panel", {}).get("id") != panel.get("panel_id"):
        raise CityOpsContractError("runtime truth queue route panel source drift")
    if sources.get("acontext_daemon_recheck", {}).get("id") != recheck.get("recheck_id"):
        raise CityOpsContractError("runtime truth queue daemon recheck source drift")
    derived = queue.get("derived_from", {})
    if derived.get("read_only") is not True:
        raise CityOpsContractError("runtime truth queue must stay read-only")
    for flag in [
        "raw_conversation_reopened",
        "raw_worker_evidence_reopened",
        "unreviewed_memory_reopened",
        "private_operator_context_reopened",
        "starts_docker_desktop",
        "pulls_container_images",
        "starts_compose_services",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "changes_irc_runtime_session_manager",
        "enables_cross_project_autorouting",
        "writes_customer_copy",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "reverifies_payment_coverage",
        "reverifies_production_infrastructure",
        "exposes_gps_or_metadata",
        "publishes_worker_doctrine",
    ]:
        if derived.get(flag) is not False:
            raise CityOpsContractError(f"runtime truth queue derived drift: {flag}")
    access_policy = queue.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("runtime truth queue audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("runtime truth queue requires admin context")
    for flag, expected in RUNTIME_TRUTH_QUEUE_FALSE_ACCESS_FLAGS.items():
        if access_policy.get(flag) is not expected:
            raise CityOpsContractError(f"runtime truth queue access drift: {flag}")
    for flag, expected in RUNTIME_TRUTH_QUEUE_READINESS_FLAGS.items():
        if queue.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"runtime truth queue readiness drift: {flag}")
    gates = queue.get("runtime_truth_gates", [])
    if [gate.get("gate") for gate in gates] != [
        "docker_daemon_socket",
        "required_image_inventory",
        "local_acontext_services",
        "empty_readiness_gate",
        "single_live_write_retrieve_parity_attempt",
    ]:
        raise CityOpsContractError("runtime truth queue gate order drift")
    for gate in gates:
        if gate.get("passed") is not False:
            raise CityOpsContractError(f"runtime truth queue gate promoted: {gate.get('gate')}")
        if gate.get("authorizes_live_attempt") is not False:
            raise CityOpsContractError(f"runtime truth queue live attempt authorized: {gate.get('gate')}")
    safe_to_claim = queue.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim_yet = queue.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    if AAS_SYSTEM_INTEGRATION_RUNTIME_TRUTH_QUEUE_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("runtime truth queue missing safe claim")
    missing = sorted(set(RUNTIME_TRUTH_QUEUE_BLOCKED_CLAIMS) - set(do_not_claim_yet))
    if missing:
        raise CityOpsContractError(f"runtime truth queue missing blocked claims: {missing}")
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)


def _assert_no_claim_overlap(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"runtime truth queue claim overlap: {overlap}")


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
