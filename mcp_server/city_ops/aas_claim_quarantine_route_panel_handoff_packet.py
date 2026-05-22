"""Handoff packet joining the AAS claim quarantine route and prevented panel.

This module creates one compact internal/admin pickup artifact over the existing
claim-quarantine route mount manifest and the prevented-claim panel. It does not
add a route, does not broaden access, and does not promote any customer,
publication, dispatch, reputation, runtime, payment, GPS/metadata, domain, or
worker-doctrine claim.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_claim_quarantine_admin_route import (
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME,
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SAFE_CLAIM,
    INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SCHEMA,
    ROUTE_FALSE_ACCESS_FLAGS,
    ROUTE_FALSE_READINESS_FLAGS,
    ROUTE_MOUNT_BLOCKED_CLAIMS,
    build_internal_admin_aas_claim_quarantine_route_mount_manifest,
)
from .aas_claim_quarantine_prevented_claim_panel import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SCHEMA,
    PANEL_ACCESS_FALSE_FLAGS,
    PANEL_BLOCKED_CLAIMS,
    PANEL_FALSE_FLAGS,
    PANEL_READINESS_FALSE_FLAGS,
    load_aas_claim_quarantine_prevented_claim_panel,
)
from .aas_claim_quarantine_read_surface import (
    AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME,
    AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
    READ_SURFACE_BLOCKED_CLAIMS,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SCHEMA = (
    "city_ops.aas_claim_quarantine_route_panel_handoff_packet.v1"
)
AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME = (
    "aas_claim_quarantine_route_panel_handoff_packet.json"
)
AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SAFE_CLAIM = (
    "internal_admin_aas_claim_quarantine_route_panel_handoff_packet_landed"
)

HANDOFF_ID = "execution_market.aas.claim_quarantine.route_panel_handoff.2026_05_22"
HANDOFF_SCOPE = "internal_admin_route_and_prevented_claim_panel_pickup_only"
HANDOFF_VERDICT = "claim_quarantine_route_panel_handoff_ready_stop_customer_dispatch_expansion"

HANDOFF_BLOCKED_CLAIMS = [
    "handoff_packet_is_human_approval_record",
    "handoff_packet_approves_customer_copy",
    "handoff_packet_authorizes_customer_delivery",
    "handoff_packet_authorizes_publication",
    "handoff_packet_registers_public_or_catalog_route",
    "handoff_packet_approves_public_price_or_quote",
    "handoff_packet_authorizes_controlled_pilot_or_queue_launch",
    "handoff_packet_authorizes_dispatch",
    "handoff_packet_authorizes_erc8004_reputation",
    "handoff_packet_proves_worker_skill_dna",
    "handoff_packet_proves_live_acontext_or_runtime_parity",
    "handoff_packet_reverifies_payment_or_production",
    "handoff_packet_allows_exact_gps_or_raw_metadata",
    "handoff_packet_grants_domain_legal_notarial_custody_or_incident_authority",
    "handoff_packet_creates_worker_copyable_aas_doctrine",
]

HANDOFF_FALSE_ACCESS_FLAGS = {
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "writes_municipal_memory": False,
    "emits_reputation_receipts": False,
    "exposes_gps_or_metadata": False,
    "publishes_worker_doctrine": False,
}

HANDOFF_READINESS_FLAGS = {
    "handoff_packet_landed": True,
    "source_route_manifest_verified": True,
    "source_prevented_panel_verified": True,
    "daytime_pickup_ready": True,
    "internal_admin_route_boundary_ready": True,
    "prevented_claim_panel_ready_for_review_learning": True,
    "customer_copy_ready": False,
    "customer_delivery_ready": False,
    "publication_ready": False,
    "public_or_catalog_route_ready": False,
    "pricing_or_customer_quote_ready": False,
    "controlled_pilot_ready": False,
    "operator_queue_launch_ready": False,
    "dispatch_ready": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "live_acontext_runtime_parity_ready": False,
    "payment_or_production_reverified": False,
    "exact_gps_or_raw_metadata_release_ready": False,
    "domain_authority_ready": False,
    "worker_copyable_doctrine_ready": False,
    "route_expansion_paused": True,
}


def build_aas_claim_quarantine_route_panel_handoff_packet(
    *,
    artifact_dir: str | Path | None = None,
    route_mount_manifest: dict[str, Any] | None = None,
    prevented_claim_panel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin route+panel handoff packet."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    manifest = route_mount_manifest or load_aas_claim_quarantine_route_mount_manifest(
        artifact_dir=base_dir
    )
    panel = prevented_claim_panel or load_aas_claim_quarantine_prevented_claim_panel(
        artifact_dir=base_dir
    )
    _assert_route_mount_manifest_contract(manifest)
    _assert_prevented_claim_panel_contract(panel)

    safe_to_claim = _dedupe(
        [
            *manifest["claim_boundaries"]["safe_to_claim"],
            *panel["claim_boundaries"]["safe_to_claim"],
            AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
            INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SAFE_CLAIM,
            AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SAFE_CLAIM,
            AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *manifest["claim_boundaries"]["do_not_claim_yet"],
            *panel["claim_boundaries"]["do_not_claim_yet"],
            *READ_SURFACE_BLOCKED_CLAIMS,
            *ROUTE_MOUNT_BLOCKED_CLAIMS,
            *PANEL_BLOCKED_CLAIMS,
            *HANDOFF_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_claim_overlap(safe_to_claim, do_not_claim_yet)

    packet = {
        "schema": AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SCHEMA,
        "handoff_id": HANDOFF_ID,
        "scope": HANDOFF_SCOPE,
        "source_artifacts": {
            "route_mount_manifest": {
                "file": INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME,
                "schema": manifest["schema"],
                "id": manifest["manifest_id"],
                "safe_claim": INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SAFE_CLAIM,
                "digest_sha256": _stable_digest(manifest),
            },
            "prevented_claim_panel": {
                "file": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
                "schema": panel["schema"],
                "id": panel["panel_id"],
                "safe_claim": AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SAFE_CLAIM,
                "digest_sha256": _stable_digest(panel),
            },
        },
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME,
                AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
            ],
            "consumes_only": [
                INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME,
                AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
            ],
            "raw_conversation_reopened": False,
            "raw_worker_evidence_reopened": False,
            "unreviewed_memory_reopened": False,
            "private_operator_context_reopened": False,
            "semantic_reinterpretation_performed": False,
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
        },
        "access_policy": {
            "audience": "internal_admin_only",
            "requires_admin_context": True,
            **HANDOFF_FALSE_ACCESS_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "handoff_cards": _handoff_cards(manifest, panel, safe_to_claim, do_not_claim_yet),
        "coordination_patterns": _coordination_patterns(manifest, panel),
        "recommended_next_actions": [
            "Use this packet as the single deterministic pickup artifact for the claim-quarantine route plus prevented-claim panel.",
            "Run the focused route/panel/handoff gate and full city-ops suite before broadening this seam.",
            "If continuing product work, choose a human-operator approval-record path; do not infer approval from route mount, panel, or handoff existence.",
        ],
        "not_next_actions": [
            "Do not create customer copy, delivery, publication, or public/catalog routes from this packet.",
            "Do not start pricing, pilot launch, operator queue launch, dispatch, ERC-8004 reputation, or worker Skill DNA from this packet.",
            "Do not treat this packet as live Acontext/runtime parity, payment/production reverification, GPS/raw metadata release, domain authority, or worker-copyable doctrine.",
        ],
        "readiness": dict(HANDOFF_READINESS_FLAGS),
        "claim_boundary_footer": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
            "safe_claim_count": len(safe_to_claim),
            "blocked_claim_count": len(do_not_claim_yet),
            "prevented_claim_count": panel["prevented_claim_summary"][
                "prevented_claim_count"
            ],
        },
        "handoff_verdict": HANDOFF_VERDICT,
    }
    _assert_handoff_packet_contract(packet, manifest, panel)
    return packet


def load_aas_claim_quarantine_route_mount_manifest(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load the persisted route manifest or rebuild it deterministically."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    path = base_dir / INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
    else:
        manifest = build_internal_admin_aas_claim_quarantine_route_mount_manifest()
    _assert_route_mount_manifest_contract(manifest)
    return manifest


def load_aas_claim_quarantine_route_panel_handoff_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted handoff packet fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    path = base_dir / AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME
    payload = json.loads(path.read_text(encoding="utf-8"))
    manifest = load_aas_claim_quarantine_route_mount_manifest(artifact_dir=base_dir)
    panel = load_aas_claim_quarantine_prevented_claim_panel(artifact_dir=base_dir)
    _assert_handoff_packet_contract(payload, manifest, panel)
    return payload


def write_aas_claim_quarantine_route_panel_handoff_packet(
    artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic route+panel handoff packet fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    packet = build_aas_claim_quarantine_route_panel_handoff_packet(artifact_dir=base_dir)
    path = base_dir / AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _handoff_cards(
    manifest: dict[str, Any],
    panel: dict[str, Any],
    safe_to_claim: list[str],
    do_not_claim_yet: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "card": "route_mount_manifest",
            "manifest_id": manifest["manifest_id"],
            "verdict": manifest["manifest_verdict"],
            "mounted_route_count": manifest["mount_contract"]["mounted_route_count"],
            "routes": [
                {
                    "route_key": route["route_key"],
                    "path": route["path"],
                    "methods": route["methods"],
                    "response_source": route["response_source"],
                }
                for route in manifest["mounted_routes"]
            ],
        },
        {
            "card": "prevented_claim_panel",
            "panel_id": panel["panel_id"],
            "panel_status": panel["panel_status"],
            "prevented_bucket_count": panel["prevented_claim_summary"][
                "prevented_bucket_count"
            ],
            "prevented_claim_count": panel["prevented_claim_summary"][
                "prevented_claim_count"
            ],
        },
        {"card": "safe_to_claim", "values": safe_to_claim},
        {"card": "do_not_claim_yet", "values": do_not_claim_yet},
        {
            "card": "next_smallest_proof",
            "values": [
                "human_operator_selected_boundary_approval_record_for_any_customer_path",
                "separate_publication_or_delivery_authorization_before_customer_copy",
                "full_city_ops_gate_before_more_wiring",
            ],
        },
    ]


def _coordination_patterns(
    manifest: dict[str, Any], panel: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "pattern": "single_pickup_artifact",
            "status": "active",
            "why_it_scales": (
                "future agents can resume from route digest plus panel digest instead "
                "of reopening raw context or recomputing the whole quarantine ladder"
            ),
            "evidence": list(
                [
                    manifest["manifest_id"],
                    panel["panel_id"],
                ]
            ),
        },
        {
            "pattern": "route_mount_is_not_customer_authority",
            "status": "guardrail",
            "why_it_scales": (
                "the mounted route proves only authenticated internal/admin pass-through "
                "access, while customer/public/dispatch readiness remains false"
            ),
            "evidence": {
                "route_path": manifest["mounted_routes"][0]["path"],
                "customer_visible": manifest["access_policy"]["customer_visible"],
                "dispatch_enabled": manifest["access_policy"]["dispatch_enabled"],
            },
        },
        {
            "pattern": "prevented_claims_are_not_approvals",
            "status": "guardrail",
            "why_it_scales": (
                "the panel records claims blocked by quarantine and exact proof needed, "
                "but it does not move any prevented claim into safe_to_claim"
            ),
            "evidence": {
                "prevented_claim_count": panel["prevented_claim_summary"][
                    "prevented_claim_count"
                ],
                "claims_can_leave_without_named_proof": panel[
                    "prevented_claim_summary"
                ]["claims_can_leave_prevented_state_without_named_proof"],
            },
        },
        {
            "pattern": "adjacent_safe_and_blocked_claims",
            "status": "active",
            "why_it_scales": (
                "safe and blocked claims sit in adjacent handoff cards so night/day "
                "sessions can copy the boundary without overclaim drift"
            ),
            "evidence": {
                "safe_claim_count": len(manifest["claim_boundaries"]["safe_to_claim"])
                + len(panel["claim_boundaries"]["safe_to_claim"]),
                "blocked_claim_count": len(
                    manifest["claim_boundaries"]["do_not_claim_yet"]
                )
                + len(panel["claim_boundaries"]["do_not_claim_yet"]),
            },
        },
    ]


def _assert_route_mount_manifest_contract(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_SCHEMA:
        raise CityOpsContractError("handoff requires claim quarantine route manifest schema")
    if manifest.get("manifest_id") != "aas_claim_quarantine_route_mount_manifest:internal_admin:v1":
        raise CityOpsContractError("handoff route manifest id drift")

    derived_from = manifest.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("handoff requires read-only route manifest")
    for flag in [
        "semantic_reinterpretation_performed",
        "writes_customer_copy",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "writes_municipal_memory",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "publishes_worker_doctrine",
        "exposes_gps_or_metadata",
    ]:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(f"handoff refuses route manifest drift: {flag}")

    mount_contract = manifest.get("mount_contract", {})
    mounted_routes = manifest.get("mounted_routes", [])
    if mount_contract.get("expected_route_count") != 1:
        raise CityOpsContractError("handoff expects exactly one claim quarantine route")
    if mount_contract.get("mounted_route_count") != len(mounted_routes):
        raise CityOpsContractError("handoff route-count drift")
    if mount_contract.get("response_semantics") != "pass_through_persisted_artifact_only":
        raise CityOpsContractError("handoff refuses response semantic drift")
    if len(mounted_routes) != 1:
        raise CityOpsContractError("handoff requires one mounted route")

    route = mounted_routes[0]
    if route.get("path") != "/internal/admin/city-ops/aas-claim-quarantine":
        raise CityOpsContractError("handoff route path drift")
    if route.get("methods") != ["GET"]:
        raise CityOpsContractError("handoff refuses method drift")
    if "verify_internal_admin_key" not in route.get("dependency_names", []):
        raise CityOpsContractError("handoff requires admin auth dependency")
    for flag in [
        "public_or_customer_visible",
        "writes_live_acontext",
        "dispatch_enabled",
        "emits_reputation_receipts",
    ]:
        if route.get(flag) is not False:
            raise CityOpsContractError(f"handoff refuses route access drift: {flag}")

    access_policy = manifest.get("access_policy", {})
    if access_policy.get("audience") != "internal_admin_only":
        raise CityOpsContractError("handoff audience drift")
    if access_policy.get("requires_admin_context") is not True:
        raise CityOpsContractError("handoff requires admin context")
    for flag in ROUTE_FALSE_ACCESS_FLAGS:
        if access_policy.get(flag) is not False:
            raise CityOpsContractError(f"handoff refuses route access flag drift: {flag}")

    readiness = manifest.get("readiness", {})
    for flag in [
        "app_level_router_include_smoke_passed",
        "expected_route_registered",
        "admin_auth_boundary_proven",
        "pass_through_response_semantics_preserved",
    ]:
        if readiness.get(flag) is not True:
            raise CityOpsContractError(f"handoff requires route readiness: {flag}")
    for flag, expected in ROUTE_FALSE_READINESS_FLAGS.items():
        if expected is False and readiness.get(flag) is not False:
            raise CityOpsContractError(f"handoff refuses promoted route readiness: {flag}")
    _assert_no_claim_overlap(
        manifest.get("claim_boundaries", {}).get("safe_to_claim", []),
        manifest.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_prevented_claim_panel_contract(panel: dict[str, Any]) -> None:
    if panel.get("schema") != AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SCHEMA:
        raise CityOpsContractError("handoff requires prevented-claim panel schema")
    if panel.get("scope") != "internal_admin_prevented_claim_panel_only_no_customer_exposure":
        raise CityOpsContractError("handoff panel scope drift")
    if panel.get("panel_status") != "quarantined_claims_recorded_as_prevented_review_claims":
        raise CityOpsContractError("handoff panel status drift")

    derived_from = panel.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("handoff requires read-only prevented panel")
    if derived_from.get("consumes_only") != [AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME]:
        raise CityOpsContractError("handoff panel consumes unexpected artifacts")
    for flag in [
        "semantic_reinterpretation_performed",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "writes_customer_copy",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "reverifies_payment_coverage",
        "reverifies_production_infrastructure",
        "exposes_gps_or_metadata",
        "publishes_worker_doctrine",
    ]:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(f"handoff refuses panel derived drift: {flag}")

    for flag in PANEL_FALSE_FLAGS:
        if panel.get(flag) is not False:
            raise CityOpsContractError(f"handoff refuses panel authority drift: {flag}")
    for flag, expected in PANEL_READINESS_FALSE_FLAGS.items():
        if panel.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"handoff refuses panel readiness drift: {flag}")
    for flag in PANEL_ACCESS_FALSE_FLAGS:
        if panel.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"handoff refuses panel access drift: {flag}")

    prevented_claims = set(panel.get("claim_boundary_footer", {}).get("prevented_claims", []))
    if not prevented_claims:
        raise CityOpsContractError("handoff requires prevented claims")
    if prevented_claims & set(panel["claim_boundaries"]["safe_to_claim"]):
        raise CityOpsContractError("handoff refuses safe prevented claim")
    if not prevented_claims <= set(panel["claim_boundaries"]["do_not_claim_yet"]):
        raise CityOpsContractError("handoff requires prevented claims to remain blocked")

    _assert_no_claim_overlap(
        panel.get("claim_boundaries", {}).get("safe_to_claim", []),
        panel.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _assert_handoff_packet_contract(
    packet: dict[str, Any], manifest: dict[str, Any], panel: dict[str, Any]
) -> None:
    if packet.get("schema") != AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_SCHEMA:
        raise CityOpsContractError("invalid claim quarantine handoff schema")
    if packet.get("handoff_id") != HANDOFF_ID:
        raise CityOpsContractError("claim quarantine handoff id drift")
    if packet.get("handoff_verdict") != HANDOFF_VERDICT:
        raise CityOpsContractError("claim quarantine handoff verdict drift")

    derived_from = packet.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("handoff packet must be read-only")
    if derived_from.get("consumes_only") != [
        INTERNAL_ADMIN_AAS_CLAIM_QUARANTINE_ROUTE_MOUNT_MANIFEST_FILENAME,
        AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
    ]:
        raise CityOpsContractError("handoff consumes unexpected artifacts")
    for flag in [
        "raw_conversation_reopened",
        "raw_worker_evidence_reopened",
        "unreviewed_memory_reopened",
        "private_operator_context_reopened",
        "semantic_reinterpretation_performed",
        "adds_route",
        "writes_customer_copy",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "writes_municipal_memory",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "reverifies_payment_coverage",
        "reverifies_production_infrastructure",
        "publishes_worker_doctrine",
        "exposes_gps_or_metadata",
    ]:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(f"handoff refuses derived drift: {flag}")

    for flag in HANDOFF_FALSE_ACCESS_FLAGS:
        if packet.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"handoff refuses access drift: {flag}")
    for flag, expected in HANDOFF_READINESS_FLAGS.items():
        if packet.get("readiness", {}).get(flag) is not expected:
            raise CityOpsContractError(f"handoff readiness drift: {flag}")

    cards = packet.get("handoff_cards", [])
    if [card.get("card") for card in cards[2:4]] != ["safe_to_claim", "do_not_claim_yet"]:
        raise CityOpsContractError("handoff requires adjacent claim cards")
    if cards[2].get("values") != packet["claim_boundaries"]["safe_to_claim"]:
        raise CityOpsContractError("handoff safe claim card drift")
    if cards[3].get("values") != packet["claim_boundaries"]["do_not_claim_yet"]:
        raise CityOpsContractError("handoff blocked claim card drift")

    if packet["source_artifacts"]["route_mount_manifest"]["digest_sha256"] != _stable_digest(manifest):
        raise CityOpsContractError("handoff route digest drift")
    if packet["source_artifacts"]["prevented_claim_panel"]["digest_sha256"] != _stable_digest(panel):
        raise CityOpsContractError("handoff panel digest drift")
    if panel["claim_boundary_footer"]["prevented_claims"] and any(
        claim in packet["claim_boundaries"]["safe_to_claim"]
        for claim in panel["claim_boundary_footer"]["prevented_claims"]
    ):
        raise CityOpsContractError("handoff promoted prevented claim")

    _assert_no_claim_overlap(
        packet.get("claim_boundaries", {}).get("safe_to_claim", []),
        packet.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _assert_no_claim_overlap(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> None:
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"handoff refuses claim overlap: {overlap}")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
