"""Remaining-image ORAS cache and local Compose health observation for Acontext.

This City-as-a-Service/AAS artifact records the May 30 1 AM continuation after
the first Acontext UI image had been loaded through the ORAS OCI-layout bridge.
The same trusted cache-load method was applied to the remaining images, local
inventory reached all nine required Compose images, and the local Acontext
Compose stack started with healthy infrastructure/core/API containers.

The artifact deliberately stops before live Acontext write/retrieve parity: the
local runtime is now infrastructure-ready, but no customer/public route,
dispatch, reputation, payment, GPS/raw metadata, or worker doctrine claim is
promoted by this slice.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .acontext_compose_image_pull_attempt_log import REQUIRED_ACONTEXT_IMAGES
from .acontext_oras_oci_layout_cache_bridge import (
    ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME,
    ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SAFE_CLAIM,
    ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SCHEMA,
    load_acontext_oras_oci_layout_cache_bridge,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SCHEMA = (
    "city_ops.acontext_remaining_images_oras_compose_health.v1"
)
ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME = (
    "acontext_remaining_images_oras_compose_health.json"
)
ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SAFE_CLAIM = (
    "admin_acontext_remaining_images_oras_compose_health_landed"
)
ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_ID = (
    "execution_market.aas.acontext_remaining_images_oras_compose_health.2026_05_30_0103"
)
ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SCOPE = (
    "internal_admin_all_required_images_cached_compose_started_health_checked_no_live_parity"
)
ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_VERDICT = (
    "all_required_images_cached_and_local_compose_health_passed_live_parity_not_attempted"
)

SUPERSEDED_SOURCE_BLOCKED_CLAIMS = {
    "oras_oci_layout_cache_bridge_cached_all_required_images",
    "oras_oci_layout_cache_bridge_started_compose_services",
    "oras_oci_layout_cache_bridge_reached_acontext_api",
    "oras_oci_layout_cache_bridge_reached_acontext_dashboard",
}

ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_BLOCKED_CLAIMS = [
    "remaining_images_oras_compose_health_completed_live_acontext_write",
    "remaining_images_oras_compose_health_completed_live_acontext_retrieval",
    "remaining_images_oras_compose_health_proved_runtime_parity",
    "remaining_images_oras_compose_health_changes_irc_runtime_session_manager",
    "remaining_images_oras_compose_health_enables_cross_project_autorouting",
    "remaining_images_oras_compose_health_authorizes_customer_copy_delivery_or_publication",
    "remaining_images_oras_compose_health_authorizes_public_or_catalog_route",
    "remaining_images_oras_compose_health_authorizes_pricing_or_customer_quote",
    "remaining_images_oras_compose_health_authorizes_queue_launch_or_dispatch",
    "remaining_images_oras_compose_health_authorizes_erc8004_reputation_or_worker_skill_dna",
    "remaining_images_oras_compose_health_reverifies_payment_or_production",
    "remaining_images_oras_compose_health_allows_exact_gps_or_raw_metadata",
    "remaining_images_oras_compose_health_grants_domain_or_emergency_authority",
    "remaining_images_oras_compose_health_creates_worker_copyable_doctrine",
]

_PRESENT_IMAGE_INVENTORY = [
    {
        "image": "ghcr.io/memodb-io/acontext-ui:latest",
        "image_id": "sha256:b303d1f1894bbe356e4f70483c06a7bfe9c38bcf46a5fff5de2d8826e87ef436",
        "size_bytes": 75495958,
        "source": "prior_oras_oci_layout_cache_bridge",
    },
    {
        "image": "chrislusf/seaweedfs:4.02",
        "image_id": "sha256:04f664b7f85620429f5c612e7d4b12deccca3aa38f651a2c88ddbcd02a5be200",
        "size_bytes": 76935649,
        "source": "docker.io/chrislusf/seaweedfs:4.02",
        "layout_bytes": 76936066,
    },
    {
        "image": "pgvector/pgvector:pg16",
        "image_id": "sha256:0a07c4114ba6d1d04effcce3385e9f5ce305eb02e56a3d35948a415a52f193ec",
        "size_bytes": 182489171,
        "source": "pre_existing_local_inventory",
    },
    {
        "image": "redis:7.4",
        "image_id": "sha256:025f550d76926c42133651436bbc9db0cd84a251f41a734050994a376036d730",
        "size_bytes": 43478644,
        "source": "docker.io/library/redis:7.4",
        "layout_bytes": 43479666,
    },
    {
        "image": "rabbitmq:4-management",
        "image_id": "sha256:3d497e721d53d477888251a350a5df25187a97e87e2790f79f50cb931adf3c4b",
        "size_bytes": 115752623,
        "source": "docker.io/library/rabbitmq:4-management",
        "layout_bytes": 115753684,
    },
    {
        "image": "ghcr.io/memodb-io/acontext-api:latest",
        "image_id": "sha256:e6e6b4a15999db7447fc9e460b4e18400c742e1bf1989d9bc29abd030ccd9341",
        "size_bytes": 46760457,
        "source": "ghcr.io/memodb-io/acontext-api:latest",
        "layout_bytes": 46759255,
    },
    {
        "image": "amazon/aws-cli:2.32.6",
        "image_id": "sha256:e0f58ac0f2689db6a4ff0828744475a8bd802b2ba4620394b5f62f34a82d6573",
        "size_bytes": 124858708,
        "source": "docker.io/amazon/aws-cli:2.32.6",
        "layout_bytes": 124859135,
    },
    {
        "image": "ghcr.io/memodb-io/acontext-core:latest",
        "image_id": "sha256:f8a6c71590cd38e75e9bac9e6b2e59b2aa8a411667bb66ccb39907562f8692cd",
        "size_bytes": 136936716,
        "source": "ghcr.io/memodb-io/acontext-core:latest",
        "layout_bytes": 136935514,
    },
    {
        "image": "jaegertracing/all-in-one:1.75.0",
        "image_id": "sha256:b305a50dbfefaa7f65202a052bd0b3e1b5e03ffda24fc614902bffea6e1c623d",
        "size_bytes": 35382132,
        "source": "docker.io/jaegertracing/all-in-one:1.75.0",
        "layout_bytes": 35382559,
    },
]

_FALSE_ACCESS_FLAGS = {
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "operator_queue_launched": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "changes_irc_runtime_session_manager": False,
    "enables_cross_project_autorouting": False,
    "emits_reputation_receipts": False,
    "exposes_gps_or_metadata": False,
    "publishes_worker_doctrine": False,
}


def build_may30_0103_remaining_images_oras_compose_health_observation() -> dict[str, Any]:
    """Return sanitized facts from the remaining-image ORAS cache and health run."""

    cached_now = [
        image
        for image in _PRESENT_IMAGE_INVENTORY
        if image["source"] not in {"prior_oras_oci_layout_cache_bridge", "pre_existing_local_inventory"}
    ]
    return {
        "observation_window": "2026-05-30T01:03:00-04:00/2026-05-30T01:06:00-04:00",
        "host_scope": "local_only_no_external_publish",
        "working_directory": "~/clawd/projects/execution-market",
        "compose_working_directory": "~/clawd/infra/acontext",
        "diagnostic_reason": (
            "apply_proven_oras_oci_layout_cache_load_path_to_remaining_required_images_then_start_local_compose"
        ),
        "sanitization_policy": {
            "include_tokens": False,
            "include_env_file_values": False,
            "include_registry_credentials": False,
            "include_raw_docker_logs": False,
            "include_home_paths": False,
            "include_private_operator_context": False,
        },
        "trusted_tool": {
            "tool": "oras",
            "available": True,
            "version": "1.3.2+Homebrew",
            "cache_method": "oras copy --platform linux/arm64 --to-oci-layout-path -> tar -> docker load -> docker tag",
        },
        "remaining_image_cache_attempt": {
            "attempted": True,
            "platform": "linux/arm64",
            "required_images_total": len(REQUIRED_ACONTEXT_IMAGES),
            "new_images_cached_and_tagged": [image["image"] for image in cached_now if image["image"] != "redis:7.4"],
            "redis_note": "redis:7.4 was loaded during the first single-image probe and present before the batch pass",
            "new_or_previously_loaded_images_count": 7,
            "oras_copy_failures": [],
            "docker_load_failures": [],
            "required_tag_failures": [],
        },
        "image_inventory_after_attempt": {
            "checked": True,
            "present_required_images": _PRESENT_IMAGE_INVENTORY,
            "present_required_image_names": [image["image"] for image in _PRESENT_IMAGE_INVENTORY],
            "missing_required_images": [],
            "all_required_images_present": True,
        },
        "compose_start": {
            "attempted": True,
            "command": "docker compose -f ~/clawd/infra/acontext/.docker-compose-1411407133.yaml --env-file ~/clawd/infra/acontext/.env up -d --no-build",
            "returncode": 0,
            "network_created": True,
            "containers_created_or_reused": True,
            "services_started": True,
        },
        "compose_service_health": {
            "checked": True,
            "healthy_services": [
                "acontext-server-api",
                "acontext-server-core",
                "acontext-server-jaeger",
                "acontext-server-pg",
                "acontext-server-rabbitmq",
                "acontext-server-redis",
                "acontext-server-seaweedfs",
            ],
            "running_services_without_healthcheck": ["acontext-server-ui"],
            "exited_expected_one_shot_services": ["acontext-server-seaweedfs-setup"],
            "unhealthy_services": [],
        },
        "http_health_checks": {
            "api_health": {
                "url": "http://127.0.0.1:8029/health",
                "status_code": 200,
                "response_shape": {"code": 0, "msg": "ok"},
            },
            "core_health": {
                "url": "http://127.0.0.1:8019/health",
                "status_code": 200,
                "response_shape": {"msg": "ok"},
            },
            "ui_root": {
                "url": "http://127.0.0.1:3000",
                "status_code": 307,
                "location": "/dashboard",
                "interpreted_as_reachable_not_full_ui_validation": True,
            },
        },
        "live_acontext_write_performed": False,
        "live_acontext_retrieval_performed": False,
        "live_parity_not_attempted_reason": (
            "runtime_health_is_now_green_but_write_retrieve_contract_discovery_and_specific_sdk_or_api_smoke_test_remain_separate_gate"
        ),
    }


def build_acontext_remaining_images_oras_compose_health(
    *,
    artifact_dir: str | Path | None = None,
    oras_bridge: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic remaining-image cache and Compose health artifact."""

    source = oras_bridge or load_acontext_oras_oci_layout_cache_bridge(artifact_dir=artifact_dir)
    observed = observation or build_may30_0103_remaining_images_oras_compose_health_observation()
    _assert_oras_bridge_source(source)
    _assert_observation_conservative(observed)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SAFE_CLAIM,
            ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            claim
            for claim in source["claim_boundaries"]["do_not_claim_yet"]
            if claim not in SUPERSEDED_SOURCE_BLOCKED_CLAIMS
        ]
        + ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_BLOCKED_CLAIMS
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    artifact = {
        "schema": ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SCHEMA,
        "observation_id": ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_ID,
        "scope": ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_SCOPE,
        "source_artifacts": {
            "oras_oci_layout_cache_bridge": {
                "file": ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME,
                "schema": source["schema"],
                "id": source["observation_id"],
                "safe_claim": ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SAFE_CLAIM,
                "digest_sha256": _stable_digest(source),
                "observation_verdict": source["observation_verdict"],
            }
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "source_artifacts": [ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_FILENAME],
            "runtime_observation_performed": True,
            "reuses_proven_oras_oci_layout_path": True,
            "all_required_images_cached": True,
            "starts_compose": True,
            "checks_local_health": True,
            "performs_live_write_retrieve_parity": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
        },
        "runtime_observation": observed,
        "observation_verdict": ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_VERDICT,
        "readiness": {
            "alternate_trusted_registry_client_installed": True,
            "all_required_images_present": True,
            "compose_services_started": True,
            "compose_infra_services_healthy": True,
            "acontext_api_health_reachable": True,
            "acontext_core_health_reachable": True,
            "acontext_ui_reachable_redirect": True,
            "write_retrieve_contract_discovered": False,
            "live_acontext_write_performed": False,
            "live_acontext_retrieval_performed": False,
            "runtime_parity_proven": False,
        },
        "runtime_truth_gates": [
            {
                "gate": "all_required_images_present",
                "passed": True,
                "evidence": "all nine required Acontext Compose images inspected locally by required tag",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "compose_services_started",
                "passed": True,
                "evidence": "docker compose up -d --no-build exited 0 and created/started the stack",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "local_api_and_core_health",
                "passed": True,
                "evidence": "API /health and core /health returned 200 with ok payloads",
                "authorizes_customer_or_dispatch_claim": False,
            },
            {
                "gate": "single_live_write_retrieve_parity_attempt",
                "passed": False,
                "evidence": "not attempted; specific SDK/API write-retrieve contract discovery remains a separate gate",
                "authorizes_customer_or_dispatch_claim": False,
            },
        ],
        "operator_guidance": {
            "safe_next_step": (
                "Perform one bounded SDK/API contract-discovery smoke test against the now-running local Acontext stack, "
                "then only claim live parity if a real write and retrieval succeed."
            ),
            "stop_line": (
                "Do not publish customer copy, start dispatch, attach reputation receipts, expose GPS/raw metadata, or claim runtime parity until write/retrieve is proven."
            ),
            "not_customer_copy": True,
            "not_worker_instruction": True,
        },
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
    }
    _assert_artifact_conservative(artifact)
    return artifact


def write_acontext_remaining_images_oras_compose_health(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Write the remaining-image cache and Compose health fixture."""

    target_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME
    artifact = build_acontext_remaining_images_oras_compose_health(artifact_dir=target_dir)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_remaining_images_oras_compose_health(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the remaining-image cache and Compose health fixture."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else _default_proof_block_dir()
    path = source_dir / ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_FILENAME
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact != build_acontext_remaining_images_oras_compose_health(artifact_dir=source_dir):
        raise CityOpsContractError("remaining-image ORAS Compose health fixture drift")
    return artifact


def _assert_oras_bridge_source(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SCHEMA:
        raise CityOpsContractError("source must be ORAS OCI-layout cache bridge")
    safe = source.get("claim_boundaries", {}).get("safe_to_claim", [])
    if ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("source missing ORAS bridge safe claim")
    readiness = source.get("readiness", {})
    if readiness.get("first_required_image_present") is not True:
        raise CityOpsContractError("source must show first required image present")
    if readiness.get("all_required_images_present") is not False:
        raise CityOpsContractError("source should be superseded only from partial image inventory")


def _assert_observation_conservative(observed: dict[str, Any]) -> None:
    inventory = observed.get("image_inventory_after_attempt", {})
    compose = observed.get("compose_start", {})
    health = observed.get("compose_service_health", {})
    http = observed.get("http_health_checks", {})
    if observed.get("trusted_tool", {}).get("tool") != "oras":
        raise CityOpsContractError("observation must identify ORAS as trusted tool")
    if observed.get("remaining_image_cache_attempt", {}).get("attempted") is not True:
        raise CityOpsContractError("remaining image cache attempt must be recorded")
    if inventory.get("all_required_images_present") is not True:
        raise CityOpsContractError("all required images must be present in this artifact")
    if inventory.get("missing_required_images") != []:
        raise CityOpsContractError("missing required images must be empty")
    if inventory.get("present_required_image_names") != REQUIRED_ACONTEXT_IMAGES:
        raise CityOpsContractError("present required image order must match Compose requirements")
    if compose.get("attempted") is not True or compose.get("returncode") != 0:
        raise CityOpsContractError("compose start must have succeeded")
    if compose.get("services_started") is not True:
        raise CityOpsContractError("compose services must be started")
    if health.get("unhealthy_services") != []:
        raise CityOpsContractError("no unhealthy services allowed")
    for name in ["api_health", "core_health"]:
        if http.get(name, {}).get("status_code") != 200:
            raise CityOpsContractError(f"{name} must return 200")
    if http.get("ui_root", {}).get("status_code") != 307:
        raise CityOpsContractError("UI root must be reachable as redirect")
    if observed.get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("live write must not be claimed")
    if observed.get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("live retrieval must not be claimed")


def _assert_artifact_conservative(artifact: dict[str, Any]) -> None:
    readiness = artifact.get("readiness", {})
    for required in [
        "all_required_images_present",
        "compose_services_started",
        "compose_infra_services_healthy",
        "acontext_api_health_reachable",
        "acontext_core_health_reachable",
        "acontext_ui_reachable_redirect",
    ]:
        if readiness.get(required) is not True:
            raise CityOpsContractError(f"artifact must record successful field: {required}")
    for forbidden in [
        "write_retrieve_contract_discovered",
        "live_acontext_write_performed",
        "live_acontext_retrieval_performed",
        "runtime_parity_proven",
    ]:
        if readiness.get(forbidden) is not False:
            raise CityOpsContractError(f"promoted readiness: {forbidden}")
    if any(artifact.get("access_flags", {}).values()):
        raise CityOpsContractError("remaining-image Compose health must not enable access flags")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"safe and blocked claim overlap: {sorted(overlap)}")
    required_blocked = set(ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_BLOCKED_CLAIMS)
    if not required_blocked <= set(do_not_claim_yet):
        raise CityOpsContractError("missing remaining-image Compose health blocked claims")
    forbidden_safe_fragments = [
        "runtime_parity",
        "completed_live_acontext",
        "authorizes_customer",
        "queue_launch",
        "dispatch",
        "worker_skill_dna",
        "gps_or_raw_metadata",
    ]
    for claim in safe_to_claim:
        if any(fragment in claim for fragment in forbidden_safe_fragments):
            raise CityOpsContractError(f"unsafe remaining-image Compose health safe claim: {claim}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
