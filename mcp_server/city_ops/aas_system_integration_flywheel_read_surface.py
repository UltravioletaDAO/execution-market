"""Internal/admin read surface for the AAS system-integration flywheel.

The flywheel already connects memory/Acontext planning, IRC coordination,
cross-project decision support, observability, and payment-confidence context.
This module makes those connections readable as deterministic operator cards
without changing their authority: no live Acontext sink is written, no payment
coverage is reverified, no dispatch path is enabled, and no customer/public
packaging claim is promoted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aas_system_integration_flywheel import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_SCHEMA,
    FLYWHEEL_BLOCKED_CLAIMS,
    load_aas_system_integration_flywheel,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SCHEMA = (
    "city_ops.aas_system_integration_flywheel_read_surface.v1"
)
AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME = (
    "aas_system_integration_flywheel_read_surface.json"
)
AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM = (
    "admin_system_integration_flywheel_surface_landed"
)

SURFACE_BLOCKED_CLAIMS = [
    "live_acontext_sink_ready",
    "runtime_parity_proven",
    "live_memory_write_completed",
    "autonomous_city_dispatch_ready",
    "customer_visible_aas_packaging_ready",
    "customer_copy_ready",
    "public_route_ready",
    "operator_queue_launch_ready",
    "payment_coverage_reverified_by_this_surface",
    "production_infrastructure_reverified_by_this_surface",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_municipal_doctrine_ready",
    "raw_transcript_replay_required_for_normal_handoff",
    "exact_gps_or_metadata_exposure_allowed",
]

_FALSE_DERIVED_FLAGS = [
    "semantic_reinterpretation_performed",
    "reads_raw_transcripts",
    "reads_unreviewed_memory",
    "reads_private_operator_context",
    "writes_live_acontext",
    "writes_municipal_memory",
    "writes_customer_copy",
    "enables_dispatch_automation",
    "emits_reputation_receipts",
    "reverifies_payment_coverage",
    "reverifies_production_infrastructure",
    "exposes_gps_or_metadata",
    "publishes_worker_doctrine",
]

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
    "surface_promotes_live_readiness",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "autonomous_dispatch_ready",
    "customer_visible_packaging_ready",
    "public_route_ready",
    "payment_coverage_reverified_by_this_surface",
    "production_infrastructure_reverified_by_this_surface",
    "operator_queue_launch_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "worker_copyable_doctrine_ready",
    "gps_or_metadata_exposure_allowed",
]


def build_aas_system_integration_flywheel_read_surface(
    *,
    artifact_dir: str | Path | None = None,
    flywheel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic internal/admin cards from the flywheel artifact."""

    source_flywheel = flywheel or load_aas_system_integration_flywheel(
        artifact_dir=artifact_dir
    )
    _assert_source_flywheel_mountable(source_flywheel)

    safe_to_claim = _dedupe(
        [
            *source_flywheel["claim_boundaries"]["safe_to_claim"],
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_SAFE_CLAIM,
            AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_flywheel["claim_boundaries"]["do_not_claim_yet"],
            *FLYWHEEL_BLOCKED_CLAIMS,
            *SURFACE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    surface = {
        "schema": AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SCHEMA,
        "surface_id": f"aas_system_integration_flywheel_read_surface:{source_flywheel['flywheel_id']}",
        "source_flywheel_id": source_flywheel["flywheel_id"],
        "proof_anchor_id": source_flywheel["proof_anchor_id"],
        "coordination_session_id": source_flywheel["coordination_session_id"],
        "compact_decision_id": source_flywheel["compact_decision_id"],
        "review_packet_id": source_flywheel["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME],
            "consumes_only": [AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME],
            "forbidden_inputs": [
                "raw_transcript",
                "raw_conversation_replay",
                "unreviewed_memory",
                "private_operator_context",
                "freeform_worker_chat",
                "live_acontext_transport",
                "payment_processor_probe",
                "production_health_probe",
                "gps_or_metadata_payloads",
            ],
            "semantic_reinterpretation_performed": False,
            "reads_raw_transcripts": False,
            "reads_unreviewed_memory": False,
            "reads_private_operator_context": False,
            "writes_live_acontext": False,
            "writes_municipal_memory": False,
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
        "render_contract": {
            "render_status": "internal_admin_flywheel_read_surface_landed_not_route",
            "suggested_internal_path": "/internal/admin/city-ops/aas-system-integration-flywheel",
            "network_route_registered": False,
            "layout": "four_id_header_strength_loop_cards_sticky_claim_footer",
            "allowed_interpretation": "pass_through_flywheel_fields_only",
            "response_fields": [
                "four_id_session_header",
                "strength_cards",
                "connection_loop_cards",
                "success_metric_cards",
                "operator_next_action_cards",
                "claim_boundary_footer",
                "readiness",
            ],
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": _surface_readiness(source_flywheel),
        "four_id_session_header": _four_id_session_header(source_flywheel),
        "strength_cards": _strength_cards(source_flywheel),
        "connection_loop_cards": _connection_loop_cards(source_flywheel),
        "success_metric_cards": _success_metric_cards(source_flywheel),
        "session_management_cards": _session_management_cards(source_flywheel),
        "operator_next_action_cards": _operator_next_action_cards(source_flywheel),
        "claim_boundary_footer": _claim_boundary_footer(safe_to_claim, do_not_claim_yet),
        "source_verdict": source_flywheel["flywheel_verdict"],
        "surface_verdict": _surface_verdict(source_flywheel),
        "next_smallest_proof": list(source_flywheel["next_smallest_proof"]),
    }
    _assert_surface_conservative(surface, source_flywheel)
    return surface


def write_aas_system_integration_flywheel_read_surface(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic internal/admin flywheel read-surface fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    surface = build_aas_system_integration_flywheel_read_surface(artifact_dir=base_dir)
    path = base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME
    path.write_text(json.dumps(surface, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_system_integration_flywheel_read_surface(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted internal/admin flywheel read surface."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    with (base_dir / AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        surface = json.load(fh)
    flywheel = load_aas_system_integration_flywheel(artifact_dir=base_dir)
    _assert_surface_conservative(surface, flywheel)
    return surface


def _surface_readiness(flywheel: dict[str, Any]) -> dict[str, Any]:
    return {
        "surface_landed": True,
        "surface_promotes_live_readiness": False,
        "source_flywheel_artifact_ready": bool(
            flywheel["readiness"].get("flywheel_artifact_ready")
        ),
        "source_ready_to_attempt_live_transport": bool(
            flywheel["readiness"].get("ready_to_attempt_live_transport")
        ),
        "acontext_sink_ready": False,
        "runtime_parity_proven": False,
        "autonomous_dispatch_ready": False,
        "customer_visible_packaging_ready": False,
        "public_route_ready": False,
        "payment_coverage_reverified_by_this_surface": False,
        "production_infrastructure_reverified_by_this_surface": False,
        "operator_queue_launch_ready": False,
        "erc8004_reputation_ready": False,
        "worker_skill_dna_ready": False,
        "worker_copyable_doctrine_ready": False,
        "gps_or_metadata_exposure_allowed": False,
    }


def _four_id_session_header(flywheel: dict[str, Any]) -> dict[str, str]:
    return {
        "proof_anchor_id": flywheel["proof_anchor_id"],
        "coordination_session_id": flywheel["coordination_session_id"],
        "compact_decision_id": flywheel["compact_decision_id"],
        "review_packet_id": flywheel["review_packet_id"],
        "normal_handoff_rule": "handoff by invariant IDs; do not reopen raw transcripts",
    }


def _strength_cards(flywheel: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": item["strength"],
            "verification_badge": item["verification_level"],
            "safe_use": item["safe_use"],
            "may_be_repeated_as_freshly_reverified": False,
        }
        for item in flywheel["declared_strength_inputs"]
    ]


def _connection_loop_cards(flywheel: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "card": loop["loop"],
            "source_strength": loop["source_strength"],
            "uses_axis": loop["uses_axis"],
            "axis_state": loop["axis_state"],
            "operator_effect": loop["decision_support_effect"],
            "guardrail": loop["guardrail"],
        }
        for loop in flywheel["connection_loops"]
    ]


def _success_metric_cards(flywheel: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = flywheel["system_integration_metrics"]
    return [
        {
            "metric": "required_axis_coverage",
            "value": f"{metrics['required_axis_count']} required axes / {metrics['connection_loop_count']} loops",
        },
        {
            "metric": "ready_vs_blocked_axes",
            "value": f"{metrics['ready_axis_count_from_matrix']} ready / {metrics['blocked_axis_count_from_matrix']} blocked",
        },
        {
            "metric": "declared_strengths",
            "value": metrics["declared_strength_count"],
        },
        {
            "metric": "claim_boundary_preservation",
            "value": metrics["claim_boundary_preservation"],
        },
        {
            "metric": "future_agent_success_definition",
            "value": list(metrics["future_agent_success_definition"]),
        },
    ]


def _session_management_cards(flywheel: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "card": item["enhancement"],
            "implementation_rule": item["implementation_rule"],
        }
        for item in flywheel["session_management_enhancements"]
    ]


def _operator_next_action_cards(flywheel: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "card": item["action"],
            "why": item["why"],
            "claim_unlocked_only_if_passes": item["claim_unlocked_only_if_passes"],
            "surface_approval_granted": "false",
        }
        for item in flywheel["operator_next_actions"]
    ]


def _claim_boundary_footer(
    safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> dict[str, Any]:
    return {
        "placement": "sticky_after_every_recommendation",
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
    }


def _surface_verdict(flywheel: dict[str, Any]) -> str:
    if flywheel["readiness"].get("ready_to_attempt_live_transport"):
        return "admin_flywheel_read_surface_landed_live_transport_attemptable_not_ready"
    return "admin_flywheel_read_surface_landed_live_transport_blocked"


def _assert_source_flywheel_mountable(flywheel: dict[str, Any]) -> None:
    if flywheel.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_SCHEMA:
        raise CityOpsContractError("flywheel read surface requires system integration flywheel")
    derived = flywheel.get("derived_from", {})
    if derived.get("read_only") is not True:
        raise CityOpsContractError("flywheel read surface requires read-only source")
    if derived.get("writes_live_sink") is not False:
        raise CityOpsContractError("flywheel read surface refuses sink-writing source")
    if derived.get("payment_system_reverified") is not False:
        raise CityOpsContractError("flywheel read surface refuses payment-reverified source")
    if derived.get("production_infrastructure_reverified") is not False:
        raise CityOpsContractError("flywheel read surface refuses infra-reverified source")
    readiness = flywheel.get("readiness", {})
    for flag in (
        "flywheel_promotes_live_readiness",
        "acontext_sink_ready",
        "runtime_parity_proven",
        "autonomous_dispatch_ready",
        "customer_visible_packaging_ready",
        "worker_copyable_doctrine_ready",
    ):
        if readiness.get(flag) is not False:
            raise CityOpsContractError(f"flywheel read surface refuses promoted {flag}")
    _assert_no_blocked_claims_safe(flywheel.get("claim_boundaries", {}).get("safe_to_claim", []))


def _assert_surface_conservative(
    surface: dict[str, Any], flywheel: dict[str, Any]
) -> None:
    if surface.get("schema") != AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("flywheel read surface schema drift")
    if surface.get("source_flywheel_id") != flywheel.get("flywheel_id"):
        raise CityOpsContractError("flywheel read surface source drift")
    for field in (
        "proof_anchor_id",
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
    ):
        if surface.get(field) != flywheel.get(field):
            raise CityOpsContractError(f"flywheel read surface {field} drift")
    for flag in _FALSE_DERIVED_FLAGS:
        if surface.get("derived_from", {}).get(flag) is not False:
            raise CityOpsContractError(f"flywheel read surface promoted derived flag {flag}")
    for flag in _FALSE_ACCESS_FLAGS:
        if surface.get("access_policy", {}).get(flag) is not False:
            raise CityOpsContractError(f"flywheel read surface promoted access flag {flag}")
    for flag in _FALSE_READINESS_FLAGS:
        if surface.get("readiness", {}).get(flag) is not False:
            raise CityOpsContractError(f"flywheel read surface promoted readiness flag {flag}")
    if surface.get("render_contract", {}).get("network_route_registered") is not False:
        raise CityOpsContractError("flywheel read surface cannot register a network route")
    safe_to_claim = surface.get("claim_boundaries", {}).get("safe_to_claim", [])
    do_not_claim = surface.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    _assert_claim_boundaries(safe_to_claim, do_not_claim)
    if AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM not in safe_to_claim:
        raise CityOpsContractError("flywheel read surface missing safe claim")
    if set(flywheel["claim_boundaries"]["do_not_claim_yet"]) - set(do_not_claim):
        raise CityOpsContractError("flywheel read surface softened source blocked claims")
    if len(surface.get("strength_cards", [])) != len(flywheel["declared_strength_inputs"]):
        raise CityOpsContractError("flywheel read surface strength-card drift")
    if len(surface.get("connection_loop_cards", [])) != len(flywheel["connection_loops"]):
        raise CityOpsContractError("flywheel read surface connection-loop drift")
    footer = surface.get("claim_boundary_footer", {})
    if footer.get("placement") != "sticky_after_every_recommendation":
        raise CityOpsContractError("flywheel read surface missing sticky blocked-claim footer")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    _assert_no_blocked_claims_safe(safe_to_claim)
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(
            f"flywheel read surface claim boundary overlap: {overlap}"
        )
    missing = set(FLYWHEEL_BLOCKED_CLAIMS) | set(SURFACE_BLOCKED_CLAIMS)
    missing -= set(do_not_claim_yet)
    if missing:
        raise CityOpsContractError(
            f"flywheel read surface missing blocked claims: {sorted(missing)}"
        )


def _assert_no_blocked_claims_safe(safe_to_claim: list[str]) -> None:
    blocked_safe = sorted(
        set(safe_to_claim) & (set(FLYWHEEL_BLOCKED_CLAIMS) | set(SURFACE_BLOCKED_CLAIMS))
    )
    if blocked_safe:
        raise CityOpsContractError(
            f"flywheel read surface blocked claims marked safe: {blocked_safe}"
        )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
