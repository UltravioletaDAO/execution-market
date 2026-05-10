"""Daytime handoff packet for the internal/admin CaaS route proof.

This module deliberately does not add another route or customer surface. It
turns the app-level route mount manifest into a compact operator/agent handoff
packet so the next session can continue from the proven internal/admin boundary
without re-opening route code, raw transcripts, unreviewed memory, or private
operator context.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .decision_support_matrix_admin_route import (
    INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_FILENAME,
    INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_SAFE_CLAIM,
    INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_SCHEMA,
    build_internal_admin_decision_support_matrix_route_mount_manifest,
)
from .proof_block_artifacts import _default_proof_block_dir

DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_SCHEMA = (
    "city_ops.decision_support_route_handoff_packet.v1"
)
DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_SAFE_CLAIM = (
    "internal_admin_decision_support_route_handoff_packet_landed"
)
DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_FILENAME = (
    "decision_support_route_handoff_packet.json"
)

_FALSE_ACCESS_FLAGS = [
    "public_route_registered",
    "customer_visible",
    "worker_visible",
    "dispatch_enabled",
    "writes_live_acontext",
    "writes_municipal_memory",
    "emits_reputation_receipts",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

_FALSE_READINESS_FLAGS = [
    "public_route_ready",
    "network_route_ready",
    "customer_visible_catalog_ready",
    "customer_copy_ready",
    "worker_visible_ready",
    "polished_operator_console_ready",
    "operator_ui_ready",
    "dispatch_routing_ready",
    "dispatch_automation_ready",
    "live_acontext_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "legal_or_regulator_ready",
    "gps_or_metadata_exposure_allowed",
    "worker_copyable_municipal_doctrine_ready",
]

_ADDITIONAL_BLOCKED_CLAIMS = [
    "route_expansion_as_progress",
    "public_or_customer_route_ready",
    "customer_visible_catalog_ready",
    "customer_copy_ready",
    "dispatch_routing_ready",
    "dispatch_automation_ready",
    "live_acontext_transport_parity_landed",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "legal_or_regulator_ready",
    "exact_gps_or_metadata_exposure",
    "worker_copyable_municipal_doctrine",
]


def build_decision_support_route_handoff_packet(
    *,
    artifact_dir: str | Path | None = None,
    route_mount_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin route handoff packet."""

    manifest = route_mount_manifest or load_internal_admin_route_mount_manifest(
        artifact_dir=artifact_dir
    )
    _assert_route_mount_manifest_contract(manifest)

    safe_to_claim = _dedupe(
        [
            *manifest["claim_boundaries"]["safe_to_claim"],
            INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_SAFE_CLAIM,
            DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *manifest["claim_boundaries"]["do_not_claim_yet"],
            *_ADDITIONAL_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    handoff = {
        "schema": DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_SCHEMA,
        "handoff_id": f"decision_support_route_handoff:{manifest['manifest_id']}",
        "source_manifest_id": manifest["manifest_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_FILENAME
            ],
            "consumes_only": [
                INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_FILENAME
            ],
            "source_manifest_digest": _stable_digest(manifest),
            "semantic_reinterpretation_performed": False,
            "raw_conversation_reopened": False,
            "raw_worker_evidence_reopened": False,
            "unreviewed_memory_reopened": False,
            "private_operator_context_reopened": False,
            "adds_route": False,
            "writes_customer_copy": False,
            "writes_live_acontext": False,
            "writes_municipal_memory": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "publishes_worker_doctrine": False,
            "exposes_gps_or_metadata": False,
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            "public_route_registered": False,
            "customer_visible": False,
            "worker_visible": False,
            "dispatch_enabled": False,
            "writes_live_acontext": False,
            "writes_municipal_memory": False,
            "emits_reputation_receipts": False,
            "exposes_gps_or_metadata": False,
            "publishes_worker_doctrine": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "handoff_cards": _handoff_cards(manifest, safe_to_claim, do_not_claim_yet),
        "coordination_patterns": _coordination_patterns(manifest),
        "recommended_next_actions": [
            "Run the focused route gate and full city-ops suite before touching this seam again.",
            "If local Acontext prerequisites are real, attempt exactly one live write/retrieve parity pass using the same reviewed consumer/report fields.",
            "If Acontext prerequisites are still blocked, stop at the handoff packet and avoid adding more route layers.",
        ],
        "not_next_actions": [
            "Do not create public or customer-visible routes from this proof block.",
            "Do not turn the display adapter into a polished operator console yet.",
            "Do not start dispatch routing, reputation, worker Skill DNA, GPS/metadata exposure, or worker-copyable doctrine.",
            "Do not treat route mount success as runtime parity or live Acontext readiness.",
        ],
        "readiness": {
            "handoff_packet_landed": True,
            "source_manifest_verified": True,
            "daytime_pickup_ready": True,
            "internal_admin_route_boundary_ready": True,
            "route_expansion_paused": True,
            "app_level_router_include_smoke_passed": manifest["readiness"][
                "app_level_router_include_smoke_passed"
            ],
            "all_expected_routes_registered": manifest["readiness"][
                "all_expected_routes_registered"
            ],
            "admin_auth_boundary_proven": manifest["readiness"][
                "admin_auth_boundary_proven"
            ],
            "pass_through_response_semantics_preserved": manifest["readiness"][
                "pass_through_response_semantics_preserved"
            ],
            "public_route_ready": False,
            "network_route_ready": False,
            "customer_visible_catalog_ready": False,
            "customer_copy_ready": False,
            "worker_visible_ready": False,
            "polished_operator_console_ready": False,
            "operator_ui_ready": False,
            "dispatch_routing_ready": False,
            "dispatch_automation_ready": False,
            "live_acontext_ready": False,
            "acontext_sink_ready": False,
            "runtime_parity_proven": False,
            "erc8004_reputation_ready": False,
            "worker_skill_dna_ready": False,
            "legal_or_regulator_ready": False,
            "gps_or_metadata_exposure_allowed": False,
            "worker_copyable_municipal_doctrine_ready": False,
        },
        "handoff_verdict": (
            "route_boundary_handoff_ready_stop_route_expansion_until_live_transport_proof"
        ),
    }
    _assert_handoff_packet_contract(handoff, manifest)
    return handoff


def load_internal_admin_route_mount_manifest(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted route mount manifest, or build it deterministically."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_FILENAME
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
    else:
        manifest = build_internal_admin_decision_support_matrix_route_mount_manifest()
    _assert_route_mount_manifest_contract(manifest)
    return manifest


def write_decision_support_route_handoff_packet_fixture(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic route handoff packet fixture."""

    packet = build_decision_support_route_handoff_packet(artifact_dir=artifact_dir)
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _handoff_cards(
    manifest: dict[str, Any], safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> list[dict[str, Any]]:
    return [
        {
            "card": "source_manifest",
            "manifest_id": manifest["manifest_id"],
            "verdict": manifest["manifest_verdict"],
            "mounted_route_count": manifest["mount_contract"]["mounted_route_count"],
        },
        {
            "card": "internal_admin_routes",
            "values": [
                {
                    "route_key": route["route_key"],
                    "path": route["path"],
                    "methods": route["methods"],
                    "returns_payload_as_is": route["returns_payload_as_is"],
                }
                for route in manifest["mounted_routes"]
            ],
        },
        {"card": "safe_to_claim", "values": safe_to_claim},
        {"card": "do_not_claim_yet", "values": do_not_claim_yet},
        {
            "card": "next_smallest_proof",
            "values": [
                "full_city_ops_gate_before_more_wiring",
                "single_live_acontext_write_retrieve_parity_pass_when_prerequisites_exist",
            ],
        },
    ]


def _coordination_patterns(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "pattern": "artifact_route_boundary",
            "status": "active",
            "why_it_scales": (
                "routes return reviewed persisted artifacts as-is, so future agents "
                "coordinate through stable proof objects instead of rewriting semantics"
            ),
            "evidence": [route["path"] for route in manifest["mounted_routes"]],
        },
        {
            "pattern": "adjacent_claim_limits",
            "status": "active",
            "why_it_scales": (
                "safe and blocked claims remain adjacent in the handoff, reducing "
                "overclaim drift across night/day sessions"
            ),
            "evidence": {
                "safe_claim_count": len(manifest["claim_boundaries"]["safe_to_claim"]),
                "blocked_claim_count": len(
                    manifest["claim_boundaries"]["do_not_claim_yet"]
                ),
            },
        },
        {
            "pattern": "mount_smoke_is_not_product_readiness",
            "status": "guardrail",
            "why_it_scales": (
                "admin route availability is useful, but it must not be promoted "
                "into customer, dispatch, reputation, or live transport readiness"
            ),
            "evidence": {
                flag: manifest["readiness"][flag] for flag in _FALSE_READINESS_FLAGS
            },
        },
        {
            "pattern": "stop_route_expansion_until_transport_truth",
            "status": "recommended",
            "why_it_scales": (
                "the next multiplier is not another read surface; it is proving "
                "that reviewed meaning survives a live write/retrieve transport pass"
            ),
            "evidence": "live_acontext_ready=false and runtime_parity_proven=false",
        },
    ]


def _assert_route_mount_manifest_contract(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_SCHEMA:
        raise CityOpsContractError("route handoff requires route mount manifest schema")
    if manifest.get("manifest_id") != "decision_support_matrix_route_mount_manifest:internal_admin:v1":
        raise CityOpsContractError("route handoff manifest id drift")

    derived_from = manifest.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("route handoff requires read-only source manifest")
    for flag in [
        "semantic_reinterpretation_performed",
        "writes_customer_copy",
        "writes_live_acontext",
        "writes_municipal_memory",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "publishes_worker_doctrine",
        "exposes_gps_or_metadata",
    ]:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(f"route handoff refuses source drift: {flag}")

    mount_contract = manifest.get("mount_contract", {})
    mounted_routes = manifest.get("mounted_routes", [])
    if mount_contract.get("expected_route_count") != 2:
        raise CityOpsContractError("route handoff expects two internal/admin routes")
    if mount_contract.get("mounted_route_count") != len(mounted_routes):
        raise CityOpsContractError("route handoff route-count drift")
    if mount_contract.get("response_semantics") != "pass_through_persisted_artifacts_only":
        raise CityOpsContractError("route handoff refuses response semantic drift")

    if len(mounted_routes) != 2:
        raise CityOpsContractError("route handoff requires both mounted routes")
    for route in mounted_routes:
        if route.get("methods") != ["GET"]:
            raise CityOpsContractError("route handoff refuses method drift")
        if route.get("admin_auth_boundary_present") is not True:
            raise CityOpsContractError("route handoff requires admin auth boundary")
        if route.get("returns_payload_as_is") is not True:
            raise CityOpsContractError("route handoff requires pass-through route")
        for flag in _FALSE_ACCESS_FLAGS:
            if route.get(flag) is not False:
                raise CityOpsContractError(
                    f"route handoff refuses route access drift: {flag}"
                )

    access_policy = manifest.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("route handoff audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("route handoff requires admin context")
    for flag in _FALSE_ACCESS_FLAGS:
        if access_policy.get(flag) is not False:
            raise CityOpsContractError(f"route handoff refuses access drift: {flag}")

    readiness = manifest.get("readiness", {})
    for flag in [
        "app_level_router_include_smoke_passed",
        "all_expected_routes_registered",
        "admin_auth_boundary_proven",
        "pass_through_response_semantics_preserved",
    ]:
        if readiness.get(flag) is not True:
            raise CityOpsContractError(f"route handoff requires manifest readiness: {flag}")
    for flag in _FALSE_READINESS_FLAGS:
        if readiness.get(flag) is not False:
            raise CityOpsContractError(
                f"route handoff refuses promoted readiness: {flag}"
            )

    _assert_no_claim_overlap(
        manifest.get("claim_boundaries", {}).get("safe_to_claim", []),
        manifest.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_handoff_packet_contract(
    handoff: dict[str, Any], manifest: dict[str, Any]
) -> None:
    if handoff.get("schema") != DECISION_SUPPORT_ROUTE_HANDOFF_PACKET_SCHEMA:
        raise CityOpsContractError("invalid route handoff packet schema")
    if handoff.get("source_manifest_id") != manifest.get("manifest_id"):
        raise CityOpsContractError("route handoff source manifest mismatch")

    derived_from = handoff.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("route handoff packet must be read-only")
    if derived_from.get("consumes_only") != [
        INTERNAL_ADMIN_DECISION_SUPPORT_MATRIX_ROUTE_MOUNT_MANIFEST_FILENAME
    ]:
        raise CityOpsContractError("route handoff packet consumes unexpected artifacts")
    for flag in [
        "semantic_reinterpretation_performed",
        "raw_conversation_reopened",
        "raw_worker_evidence_reopened",
        "unreviewed_memory_reopened",
        "private_operator_context_reopened",
        "adds_route",
        "writes_customer_copy",
        "writes_live_acontext",
        "writes_municipal_memory",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "publishes_worker_doctrine",
        "exposes_gps_or_metadata",
    ]:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(f"route handoff refuses derived drift: {flag}")

    for flag in _FALSE_ACCESS_FLAGS:
        if handoff.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"route handoff refuses access drift: {flag}")
    for flag in _FALSE_READINESS_FLAGS:
        if handoff.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(
                f"route handoff refuses promoted readiness: {flag}"
            )

    cards = handoff.get("handoff_cards", [])
    if [card.get("card") for card in cards[2:4]] != ["safe_to_claim", "do_not_claim_yet"]:
        raise CityOpsContractError("route handoff requires adjacent claim cards")
    if cards[2].get("values") != handoff["claim_boundaries"]["safe_to_claim"]:
        raise CityOpsContractError("route handoff safe claim card drift")
    if cards[3].get("values") != handoff["claim_boundaries"]["do_not_claim_yet"]:
        raise CityOpsContractError("route handoff blocked claim card drift")

    _assert_no_claim_overlap(
        handoff.get("claim_boundaries", {}).get("safe_to_claim", []),
        handoff.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _assert_no_claim_overlap(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"route handoff refuses claim overlap: {overlap}")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
