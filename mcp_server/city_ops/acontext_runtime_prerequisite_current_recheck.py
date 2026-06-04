"""Current read-only Acontext runtime prerequisite recheck for AAS.

This internal/admin proof block records the 2026-06-04 00:05 EDT
City-as-a-Service Acontext prerequisite recheck.  The check is intentionally
read-only: it does not start Docker Desktop, does not pull/cache images, does
not start Compose, does not create projects/sessions/messages, and does not
write to or retrieve from Acontext.

The useful current fact is narrow: Docker is still selected on the
``desktop-linux`` context, but the local Docker daemon socket is unreachable.
Therefore fresh image inventory, container inventory, Compose health, local
Acontext API/core/UI health, and live write/retrieve parity cannot be claimed
from this session.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from .acontext_operator_activation_no_answer_pause_ledger import (
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SCHEMA,
    NO_ANSWER_PAUSE_LEDGER_BLOCKED_CLAIMS,
    load_acontext_operator_activation_no_answer_pause_ledger,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_SCHEMA = (
    "city_ops.acontext_runtime_prerequisite_current_recheck.v1"
)
ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_FILENAME = (
    "acontext_runtime_prerequisite_current_recheck.json"
)
ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_SAFE_CLAIM = (
    "admin_acontext_runtime_prerequisite_current_recheck_landed"
)
ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_ID = (
    "execution_market.aas.acontext_runtime_prerequisite_current_recheck.2026_06_04_0005"
)
ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_VERDICT = (
    "docker_daemon_unreachable_current_runtime_reverification_blocked"
)
ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_SCOPE = (
    "internal_admin_read_only_current_runtime_prerequisite_recheck_no_live_parity"
)

RUNTIME_PREREQUISITE_CURRENT_RECHECK_BLOCKED_CLAIMS = [
    *NO_ANSWER_PAUSE_LEDGER_BLOCKED_CLAIMS,
    "runtime_prerequisite_current_recheck_started_docker_desktop",
    "runtime_prerequisite_current_recheck_repaired_docker_daemon",
    "runtime_prerequisite_current_recheck_pulled_or_cached_images",
    "runtime_prerequisite_current_recheck_verified_current_required_image_inventory",
    "runtime_prerequisite_current_recheck_verified_current_container_inventory",
    "runtime_prerequisite_current_recheck_started_compose_services",
    "runtime_prerequisite_current_recheck_verified_current_compose_health",
    "runtime_prerequisite_current_recheck_reached_current_acontext_api",
    "runtime_prerequisite_current_recheck_reached_current_acontext_core",
    "runtime_prerequisite_current_recheck_reached_current_acontext_ui",
    "runtime_prerequisite_current_recheck_created_acontext_project",
    "runtime_prerequisite_current_recheck_created_acontext_session",
    "runtime_prerequisite_current_recheck_completed_live_acontext_write",
    "runtime_prerequisite_current_recheck_completed_live_acontext_retrieval",
    "runtime_prerequisite_current_recheck_proved_runtime_parity",
    "runtime_prerequisite_current_recheck_authorizes_runtime_memory_answer_record",
    "runtime_prerequisite_current_recheck_authorizes_runtime_adapter_registration",
    "runtime_prerequisite_current_recheck_authorizes_irc_session_manager_mutation",
    "runtime_prerequisite_current_recheck_authorizes_customer_public_worker_surface",
    "runtime_prerequisite_current_recheck_authorizes_catalog_pricing_queue_or_dispatch",
    "runtime_prerequisite_current_recheck_emits_erc8004_reputation_or_worker_skill_dna",
    "runtime_prerequisite_current_recheck_reverifies_payment_or_production",
    "runtime_prerequisite_current_recheck_allows_exact_gps_or_raw_metadata",
    "runtime_prerequisite_current_recheck_releases_private_context",
    "runtime_prerequisite_current_recheck_grants_domain_authority_claims",
    "runtime_prerequisite_current_recheck_publishes_worker_copyable_doctrine",
    "runtime_prerequisite_current_recheck_integrates_stopped_projects",
]

FALSE_ACCESS_FLAGS = {
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "irc_session_manager_mutated": False,
    "cross_project_autorouting_enabled": False,
    "network_route_registered": False,
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "pricing_enabled": False,
    "operator_queue_launched": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "starts_live_services": False,
    "creates_projects": False,
    "creates_sessions": False,
    "writes_messages": False,
    "retrieves_messages": False,
    "emits_reputation_receipts": False,
    "reverifies_payment_or_production": False,
    "exposes_gps_or_metadata": False,
    "releases_private_operator_context": False,
    "grants_domain_or_emergency_authority": False,
    "publishes_worker_doctrine": False,
    "integrates_stopped_projects": False,
}


def build_june04_0005_runtime_prerequisite_observation() -> dict[str, Any]:
    """Return sanitized facts from the June 4 read-only prerequisite check."""

    return {
        "observation_window": "2026-06-04T00:05:00-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "diagnostic_reason": (
            "fresh_read_only_acontext_runtime_prerequisite_recheck_after_june3_hold_state"
        ),
        "sanitization_policy": {
            "include_tokens": False,
            "include_env_file_values": False,
            "include_registry_credentials": False,
            "include_raw_docker_logs": False,
            "include_home_paths": False,
            "include_private_operator_context": False,
            "include_session_or_message_ids": False,
            "include_gps_or_raw_metadata": False,
        },
        "commands_observed": [
            "docker context ls",
            "docker info --format 'ServerVersion={{.ServerVersion}} OperatingSystem={{.OperatingSystem}} Architecture={{.Architecture}} Driver={{.Driver}}'",
            "docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.CreatedSince}} {{.Size}}' | grep required Acontext images",
            "docker ps -a --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}' | grep Acontext services",
            "curl --max-time 2 http://localhost:8029/api/v1/health",
            "curl --max-time 2 http://localhost:8089/health",
            "curl --max-time 2 http://localhost:3000",
        ],
        "docker_contexts": {
            "active_context": "desktop-linux",
            "contexts_observed": [
                {
                    "name": "default",
                    "endpoint_class": "unix_socket",
                    "active": False,
                },
                {
                    "name": "desktop-linux",
                    "description": "Docker Desktop",
                    "endpoint_class": "user_docker_socket",
                    "active": True,
                },
            ],
        },
        "docker_daemon": {
            "checked": True,
            "available": False,
            "server_version_observed": None,
            "operating_system_observed": None,
            "architecture_observed": None,
            "driver_observed": None,
            "error_class": "cannot_connect_to_user_docker_socket",
        },
        "required_image_inventory": {
            "checked": False,
            "skipped_reason": "docker_daemon_unavailable",
            "required_images_known_from_code": REQUIRED_ACONTEXT_IMAGES,
            "required_image_count": len(REQUIRED_ACONTEXT_IMAGES),
            "current_inventory_verified": False,
            "all_required_images_present_currently_verified": False,
        },
        "container_inventory": {
            "checked": False,
            "skipped_reason": "docker_daemon_unavailable",
            "current_acontext_containers_verified": False,
        },
        "local_http_checks": {
            "api_health": {
                "url": "http://localhost:8029/api/v1/health",
                "checked": True,
                "reachable": False,
                "error_class": "connection_refused",
            },
            "core_health": {
                "url": "http://localhost:8089/health",
                "checked": True,
                "reachable": False,
                "error_class": "connection_refused",
            },
            "ui_root": {
                "url": "http://localhost:3000",
                "checked": True,
                "reachable": False,
                "error_class": "connection_refused",
            },
        },
        "actions_not_taken": {
            "started_docker_desktop": False,
            "repaired_docker_daemon": False,
            "pulled_or_cached_images": False,
            "started_compose_services": False,
            "created_acontext_project": False,
            "created_acontext_session": False,
            "performed_live_acontext_write": False,
            "performed_live_acontext_retrieval": False,
            "mutated_runtime_configuration": False,
            "registered_runtime_adapter": False,
        },
    }


def build_acontext_runtime_prerequisite_current_recheck(
    *,
    artifact_dir: str | Path | None = None,
    pause_ledger: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a fail-closed current runtime prerequisite recheck artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = pause_ledger or load_acontext_operator_activation_no_answer_pause_ledger(
        artifact_dir=base_dir
    )
    observed = observation or build_june04_0005_runtime_prerequisite_observation()
    _assert_pause_ledger_source_conservative(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SAFE_CLAIM,
            ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *RUNTIME_PREREQUISITE_CURRENT_RECHECK_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME
    packet: dict[str, Any] = {
        "schema": ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_SCHEMA,
        "packet_id": ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_ID,
        "scope": ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_SCOPE,
        "status_verdict": ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_VERDICT,
        "source_artifacts": {
            "acontext_operator_activation_no_answer_pause_ledger": {
                "file": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME,
                "schema": source["schema"],
                "id": source["packet_id"],
                "safe_claim": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": _file_digest(source_file),
                "status_verdict": source["status_verdict"],
            }
        },
        "runtime_prerequisite_recheck": {
            "recheck_landed": True,
            "read_only": True,
            "current_fact": "docker_daemon_unreachable_current_runtime_reverification_blocked",
            "source_no_answer_state_preserved": True,
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "effective_decision": "hold_no_runtime_mutation",
            "docker_context_active": observed["docker_contexts"]["active_context"],
            "docker_daemon_available": observed["docker_daemon"]["available"],
            "current_required_image_inventory_verified": observed["required_image_inventory"][
                "current_inventory_verified"
            ],
            "current_container_inventory_verified": observed["container_inventory"][
                "current_acontext_containers_verified"
            ],
            "current_local_api_reachable": observed["local_http_checks"]["api_health"]["reachable"],
            "current_local_core_reachable": observed["local_http_checks"]["core_health"]["reachable"],
            "current_local_ui_reachable": observed["local_http_checks"]["ui_root"]["reachable"],
            "runtime_parity_proven": False,
            "next_truth_producing_step": (
                "restore_docker_daemon_reachability_then_rerun_read_only_inventory_before_any_compose_or_parity_attempt"
            ),
        },
        "runtime_observation": observed,
        "readiness": {
            "internal_admin_current_prerequisite_recheck_landed": True,
            "safe_for_read_only_operator_context": True,
            "safe_for_operator_answer_recording": False,
            "operator_answer_recorded": False,
            "operator_approval_recorded": False,
            "runtime_memory_answer_record_authorized": False,
            "docker_daemon_available": False,
            "current_image_inventory_verified": False,
            "current_required_images_present_verified": False,
            "current_container_inventory_verified": False,
            "current_compose_health_verified": False,
            "current_acontext_api_reachable": False,
            "current_acontext_core_reachable": False,
            "current_acontext_ui_reachable": False,
            "compose_startup_authorized": False,
            "live_acontext_write_authorized": False,
            "live_acontext_retrieval_authorized": False,
            "runtime_adapter_registration_authorized": False,
            "runtime_session_manager_mutation_authorized": False,
            "customer_or_public_delivery_authorized": False,
            "queue_launch_or_dispatch_authorized": False,
            "reputation_or_worker_skill_dna_authorized": False,
            "payment_or_production_claim_authorized": False,
            "gps_or_raw_metadata_release_authorized": False,
            "private_context_release_authorized": False,
            "domain_authority_claim_authorized": False,
            "worker_copyable_doctrine_authorized": False,
            "stopped_project_integration_authorized": False,
            "runtime_parity_proven": False,
            "remaining_blockers": [
                "explicit_operator_answer_absent",
                "operator_approval_record_absent",
                "docker_daemon_socket_unreachable",
                "current_required_image_inventory_not_verified",
                "current_container_inventory_not_verified",
                "current_compose_health_not_verified",
                "current_local_api_core_ui_unreachable",
                "live_write_retrieve_parity_not_attempted",
            ],
        },
        "access_flags": dict(FALSE_ACCESS_FLAGS),
        "stopped_project_firewall": {
            "autojob_work_allowed": False,
            "frontier_academy_work_allowed": False,
            "kk_v2_work_allowed": False,
            "karmacadabra_v2_work_allowed": False,
            "source": "DREAM-PRIORITIES.md explicit stop list",
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_guidance": {
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "not_dashboard_spec": True,
            "records_no_answer": True,
            "records_no_approval": True,
            "if_no_human_answer": "keep_both_lanes_held_or_pause_proof_layering",
            "if_runtime_memory_later_selected": (
                "first_restore_docker_daemon_reachability_and_rerun_read_only_inventory; then seek separate approval before compose_start_or_live_parity"
            ),
            "stop_line": (
                "This current recheck records only Docker daemon unreachability and local service refusal. "
                "It is not an operator answer, not an approval, not runtime parity, and not authority for Compose startup, live Acontext writes/retrievals, runtime mutation, product exposure, dispatch, reputation, payment/production claims, GPS/raw metadata release, private-context release, authority claims, worker doctrine, or stopped-project integration."
            ),
        },
    }
    _assert_packet_conservative(packet)
    return packet


def write_acontext_runtime_prerequisite_current_recheck(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the current prerequisite recheck artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_FILENAME
    payload = build_acontext_runtime_prerequisite_current_recheck(artifact_dir=base_dir)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_runtime_prerequisite_current_recheck(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted current prerequisite recheck artifact."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    _assert_packet_conservative(payload)
    return payload


def _stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _assert_pause_ledger_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SCHEMA:
        raise CityOpsContractError("runtime prerequisite recheck source schema drift")
    safe = set(source.get("claim_boundaries", {}).get("safe_to_claim", []))
    if ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SAFE_CLAIM not in safe:
        raise CityOpsContractError("runtime prerequisite recheck source safe claim missing")
    ledger = source.get("no_answer_pause_ledger", {})
    if ledger.get("explicit_operator_answer_present") is not False:
        raise CityOpsContractError("runtime prerequisite recheck source records operator answer")
    if ledger.get("operator_approval_record_present") is not False:
        raise CityOpsContractError("runtime prerequisite recheck source records operator approval")
    if ledger.get("effective_decision_after_pause") != "hold_no_runtime_mutation":
        raise CityOpsContractError("runtime prerequisite recheck source decision promoted")
    readiness = source.get("readiness", {})
    if readiness.get("runtime_parity_proven") is not False:
        raise CityOpsContractError("runtime prerequisite recheck source runtime parity promoted")
    if any(source.get("access_flags", {}).values()):
        raise CityOpsContractError("runtime prerequisite recheck source access flag promoted")


def _assert_observation_conservative(observation: dict[str, Any]) -> None:
    policy = observation.get("sanitization_policy", {})
    for key, value in policy.items():
        if value is not False:
            raise CityOpsContractError(f"runtime prerequisite recheck sanitization drift: {key}")
    if observation.get("docker_contexts", {}).get("active_context") != "desktop-linux":
        raise CityOpsContractError("runtime prerequisite recheck Docker context drift")
    if observation.get("docker_daemon", {}).get("available") is not False:
        raise CityOpsContractError("runtime prerequisite recheck expects Docker daemon unavailable")
    inventory = observation.get("required_image_inventory", {})
    if inventory.get("checked") is not False:
        raise CityOpsContractError("runtime prerequisite recheck must not verify image inventory")
    if inventory.get("required_images_known_from_code") != REQUIRED_ACONTEXT_IMAGES:
        raise CityOpsContractError("runtime prerequisite recheck required image list drift")
    containers = observation.get("container_inventory", {})
    if containers.get("checked") is not False:
        raise CityOpsContractError("runtime prerequisite recheck must not verify containers")
    for name, check in observation.get("local_http_checks", {}).items():
        if check.get("reachable") is not False:
            raise CityOpsContractError(f"runtime prerequisite recheck unexpectedly reached {name}")
    actions = observation.get("actions_not_taken", {})
    for key, value in actions.items():
        if value is not False:
            raise CityOpsContractError(f"runtime prerequisite recheck action taken unexpectedly: {key}")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(
            f"runtime prerequisite recheck claim boundary overlap: {sorted(overlap)}"
        )
    forbidden_safe_fragments = [
        "operator_answer",
        "operator_approval",
        "runtime_parity",
        "started_compose",
        "live_acontext_write",
        "live_acontext_retrieval",
        "customer_public_worker_surface",
        "queue_or_dispatch",
        "worker_skill_dna",
        "exact_gps",
        "private_context",
        "stopped_project",
    ]
    for claim in safe_to_claim:
        for fragment in forbidden_safe_fragments:
            if fragment in claim:
                raise CityOpsContractError(
                    f"runtime prerequisite recheck forbidden safe claim: {claim}"
                )


def _assert_packet_conservative(packet: dict[str, Any]) -> None:
    if packet.get("schema") != ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_SCHEMA:
        raise CityOpsContractError("runtime prerequisite recheck schema drift")
    if packet.get("status_verdict") != ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_VERDICT:
        raise CityOpsContractError("runtime prerequisite recheck verdict drift")
    summary = packet.get("runtime_prerequisite_recheck", {})
    if summary.get("explicit_operator_answer_present") is not False:
        raise CityOpsContractError("runtime prerequisite recheck records operator answer")
    if summary.get("operator_approval_record_present") is not False:
        raise CityOpsContractError("runtime prerequisite recheck records operator approval")
    if summary.get("docker_daemon_available") is not False:
        raise CityOpsContractError("runtime prerequisite recheck daemon availability promoted")
    if summary.get("runtime_parity_proven") is not False:
        raise CityOpsContractError("runtime prerequisite recheck runtime parity promoted")
    readiness = packet.get("readiness", {})
    for key, value in readiness.items():
        if key in {
            "internal_admin_current_prerequisite_recheck_landed",
            "safe_for_read_only_operator_context",
        }:
            if value is not True:
                raise CityOpsContractError(f"runtime prerequisite recheck readiness false: {key}")
        elif isinstance(value, bool) and value is not False:
            raise CityOpsContractError(f"runtime prerequisite recheck readiness promoted: {key}")
    if any(packet.get("access_flags", {}).values()):
        raise CityOpsContractError("runtime prerequisite recheck access flag promoted")
    blocked = set(packet.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(RUNTIME_PREREQUISITE_CURRENT_RECHECK_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"runtime prerequisite recheck missing blocked claims: {sorted(missing)}"
        )
    _assert_claim_boundaries(
        packet.get("claim_boundaries", {}).get("safe_to_claim", []),
        packet.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    _assert_observation_conservative(packet.get("runtime_observation", {}))
