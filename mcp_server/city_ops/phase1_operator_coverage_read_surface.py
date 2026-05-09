"""Internal/admin-only read surface for Phase 1 CaaS operator coverage.

This is a conservative mount contract over the persisted operator coverage
renderer.  It exposes the renderer payload as data for an internal/admin-only
consumer without registering a public route, customer copy, worker instructions,
dispatch automation, live Acontext writes, reputation updates, GPS/metadata
exposure, or legal/regulator claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_operator_coverage_renderer import (
    PHASE1_OPERATOR_COVERAGE_RENDERER_BLOCKED_CLAIMS,
    PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME,
    PHASE1_OPERATOR_COVERAGE_RENDERER_SAFE_CLAIM,
    PHASE1_OPERATOR_COVERAGE_RENDERER_SCHEMA,
    load_phase1_operator_coverage_renderer,
)

PHASE1_OPERATOR_COVERAGE_READ_SURFACE_SCHEMA = (
    "city_ops.phase1_operator_coverage_read_surface.v1"
)
PHASE1_OPERATOR_COVERAGE_READ_SURFACE_SAFE_CLAIM = (
    "phase1_operator_coverage_read_surface_landed"
)
PHASE1_OPERATOR_COVERAGE_READ_SURFACE_FILENAME = (
    "phase1_operator_coverage_read_surface.json"
)

# Surface-level claims that remain blocked even though the read surface contract
# exists.  This surface is data-only and internal/admin-only; it is not the
# polished console, customer catalog, dispatch router, or worker doctrine.
PHASE1_OPERATOR_COVERAGE_READ_SURFACE_BLOCKED_CLAIMS = [
    "public_route_ready",
    "customer_visible_catalog_ready",
    "customer_copy_ready",
    "polished_operator_console_ready",
    "operator_ui_ready",
    "worker_instruction_surface_ready",
    "dispatch_routing_ready",
    "dispatch_automation_ready",
    "live_acontext_readiness",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "legal_sufficiency",
    "regulator_acceptance",
    "exact_gps_or_metadata_exposure",
    "worker_copyable_municipal_doctrine",
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

_FALSE_DERIVED_FLAGS = [
    "semantic_reinterpretation_performed",
    "reads_raw_review_fixtures",
    "reads_raw_transcripts",
    "writes_customer_copy",
    "writes_live_acontext",
    "writes_municipal_memory",
    "enables_dispatch_automation",
    "emits_reputation_receipts",
    "publishes_worker_doctrine",
    "exposes_gps_or_metadata",
]


def build_phase1_operator_coverage_read_surface(
    *,
    fixture_dir: str | Path | None = None,
    renderer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an internal/admin-only read surface from the renderer artifact.

    By default the surface loads the persisted renderer artifact, which itself
    loads and validates the persisted summary.  Tests may pass a renderer object
    directly to prove drift rejection, but this builder still enforces surface-
    local conservative checks before exposing anything.
    """

    source_renderer = renderer or load_phase1_operator_coverage_renderer(
        fixture_dir=fixture_dir
    )
    _assert_renderer_mountable(source_renderer)

    safe_to_claim = _dedupe(
        [
            *source_renderer["claim_boundaries"]["safe_to_claim"],
            PHASE1_OPERATOR_COVERAGE_RENDERER_SAFE_CLAIM,
            PHASE1_OPERATOR_COVERAGE_READ_SURFACE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_renderer["claim_boundaries"]["do_not_claim_yet"],
            *PHASE1_OPERATOR_COVERAGE_RENDERER_BLOCKED_CLAIMS,
            *PHASE1_OPERATOR_COVERAGE_READ_SURFACE_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    surface = {
        "schema": PHASE1_OPERATOR_COVERAGE_READ_SURFACE_SCHEMA,
        "surface_id": f"operator_coverage_read_surface:{source_renderer['renderer_id']}",
        "source_renderer_id": source_renderer["renderer_id"],
        "source_summary_id": source_renderer["source_summary_id"],
        "source_registry_id": source_renderer["source_registry_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME],
            "consumes_only": [PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME],
            "forbidden_inputs": [
                "raw_transcript",
                "raw_review_fixture",
                "unreviewed_memory",
                "freeform_worker_chat",
                "private_operator_context",
                "live_acontext_transport",
                "gps_or_metadata_payloads",
            ],
            "semantic_reinterpretation_performed": False,
            "reads_raw_review_fixtures": False,
            "reads_raw_transcripts": False,
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
        "mount_contract": {
            "mount_status": "internal_admin_read_surface_contract_landed_not_public_route",
            "method": "GET",
            "suggested_internal_path": "/internal/admin/city-ops/phase1/operator-coverage",
            "network_route_registered": False,
            "response_fields": [
                "coverage_totals",
                "coverage_table",
                "display_lines",
                "claim_boundaries",
                "readiness",
            ],
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "coverage_totals": dict(source_renderer["coverage_totals"]),
        "coverage_table": [dict(row) for row in source_renderer["coverage_table"]],
        "display_lines": list(source_renderer["display_lines"]),
        "readiness": {
            "read_surface_promotes_readiness": False,
            "public_route_ready": False,
            "customer_visible_catalog_ready": False,
            "customer_copy_ready": False,
            "polished_operator_console_ready": False,
            "operator_ui_ready": False,
            "worker_instruction_surface_ready": False,
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
        "read_surface_cards": _read_surface_cards(source_renderer, safe_to_claim, do_not_claim_yet),
        "surface_verdict": "phase1_operator_coverage_read_surface_landed_internal_admin_only_not_public",
        "next_smallest_proof": (
            "Wire this contract to a real authenticated internal/admin route only after an admin auth boundary exists. "
            "Keep response fields identical to the persisted surface payload, and do not add customer copy, "
            "dispatch routing, live Acontext writes, reputation updates, worker Skill DNA, legal/regulator claims, "
            "GPS/metadata exposure, or worker-copyable doctrine."
        ),
    }
    _assert_read_surface_conservative(surface)
    return surface


def write_phase1_operator_coverage_read_surface(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic internal/admin read-surface payload."""

    surface = build_phase1_operator_coverage_read_surface(fixture_dir=fixture_dir)
    base_dir = _operator_coverage_read_surface_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_OPERATOR_COVERAGE_READ_SURFACE_FILENAME
    path.write_text(json.dumps(surface, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_phase1_operator_coverage_read_surface(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted internal/admin read-surface payload."""

    path = _operator_coverage_read_surface_dir(fixture_dir) / PHASE1_OPERATOR_COVERAGE_READ_SURFACE_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        surface = json.load(fh)
    if not isinstance(surface, dict):
        raise CityOpsContractError("operator coverage read surface artifact must be a JSON object")
    _assert_read_surface_conservative(surface)
    return surface


def _operator_coverage_read_surface_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    from .phase1_review_output_schemas import OFFER_SPEC_DIR

    return OFFER_SPEC_DIR / "reviewed_outputs"


def _read_surface_cards(
    renderer: dict[str, Any], safe_to_claim: list[str], do_not_claim_yet: list[str]
) -> list[dict[str, Any]]:
    return [
        {
            "card": "coverage_totals",
            "status": "visible_internal_admin_only",
            "values": dict(renderer["coverage_totals"]),
        },
        {
            "card": "safe_to_claim",
            "status": "visible_without_softening",
            "values": list(safe_to_claim),
        },
        {
            "card": "do_not_claim_yet",
            "status": "visible_without_softening",
            "values": list(do_not_claim_yet),
        },
        {
            "card": "phase1_offer_rows",
            "status": "renderer_payload_pass_through",
            "values": [
                {
                    "offer_id": row["offer_id"],
                    "fixture_id": row["fixture_id"],
                    "outcome_status": row["outcome_status"],
                    "follow_on_task_trigger": row["follow_on_task_trigger"],
                }
                for row in renderer["coverage_table"]
            ],
        },
    ]


def _assert_renderer_mountable(renderer: dict[str, Any]) -> None:
    if renderer.get("schema") != PHASE1_OPERATOR_COVERAGE_RENDERER_SCHEMA:
        raise CityOpsContractError("operator coverage read surface expected renderer schema")
    derived_from = renderer.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("operator coverage read surface requires read-only renderer")
    if derived_from.get("consumes_only") != ["phase1_operator_coverage_summary.json"]:
        raise CityOpsContractError("operator coverage read surface requires summary-only renderer")
    for flag in [
        "writes_customer_copy",
        "writes_live_acontext",
        "enables_dispatch_automation",
        "publishes_worker_doctrine",
        "reads_raw_review_fixtures",
        "reads_raw_transcripts",
    ]:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(
                f"operator coverage read surface rejects renderer overclaim: {flag}"
            )

    readiness = renderer.get("readiness", {})
    promoted = [flag for flag, value in readiness.items() if value is True]
    if promoted:
        raise CityOpsContractError(
            f"operator coverage read surface refuses promoted renderer readiness: {promoted}"
        )

    rows = renderer.get("coverage_table")
    if not isinstance(rows, list) or not rows:
        raise CityOpsContractError("operator coverage read surface requires renderer rows")
    if renderer.get("coverage_totals", {}).get("reviewed_fixture_count") != len(rows):
        raise CityOpsContractError("operator coverage read surface fixture count drift")
    for row in rows:
        if row.get("readiness_promoted") is not False:
            raise CityOpsContractError("operator coverage read surface refuses promoted row readiness")
        _assert_claim_boundaries(
            list(row.get("safe_to_claim", [])), list(row.get("do_not_claim_yet", []))
        )


def _assert_read_surface_conservative(surface: dict[str, Any]) -> None:
    if surface.get("schema") != PHASE1_OPERATOR_COVERAGE_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("operator coverage read surface schema mismatch")
    derived_from = surface.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("operator coverage read surface must stay read-only")
    if derived_from.get("consumes_only") != [PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME]:
        raise CityOpsContractError("operator coverage read surface must consume only renderer artifact")
    for flag in _FALSE_DERIVED_FLAGS:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(f"operator coverage read surface overclaims {flag}")

    access = surface.get("access_policy", {})
    if access.get("audience") != "internal_admin_only":
        raise CityOpsContractError("operator coverage read surface must stay internal/admin-only")
    if access.get("requires_admin_context") is not True:
        raise CityOpsContractError("operator coverage read surface requires admin context")
    for flag in _FALSE_ACCESS_FLAGS:
        if access.get(flag) is not False:
            raise CityOpsContractError(f"operator coverage read surface access overclaims {flag}")

    mount = surface.get("mount_contract", {})
    if mount.get("network_route_registered") is not False:
        raise CityOpsContractError("operator coverage read surface must not claim registered route")
    if mount.get("method") != "GET":
        raise CityOpsContractError("operator coverage read surface must be read-only GET")

    boundaries = surface.get("claim_boundaries", {})
    _assert_claim_boundaries(
        list(boundaries.get("safe_to_claim", [])),
        list(boundaries.get("do_not_claim_yet", [])),
    )
    blocked = set(boundaries["do_not_claim_yet"])
    missing_blocked = [
        claim
        for claim in PHASE1_OPERATOR_COVERAGE_READ_SURFACE_BLOCKED_CLAIMS
        if claim not in blocked
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"operator coverage read surface missing blocked claims: {missing_blocked}"
        )

    readiness = surface.get("readiness", {})
    promoted = [flag for flag, value in readiness.items() if value is True]
    if promoted:
        raise CityOpsContractError(
            f"operator coverage read surface promoted readiness: {promoted}"
        )

    for row in surface.get("coverage_table", []):
        if row.get("readiness_promoted") is not False:
            raise CityOpsContractError("operator coverage read surface row promoted readiness")
        _assert_claim_boundaries(
            list(row.get("safe_to_claim", [])), list(row.get("do_not_claim_yet", []))
        )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    if not safe_to_claim:
        raise CityOpsContractError("operator coverage read surface missing safe_to_claim")
    if not do_not_claim_yet:
        raise CityOpsContractError("operator coverage read surface missing do_not_claim_yet")
    forbidden_safe = sorted(
        set(safe_to_claim)
        & set(PHASE1_OPERATOR_COVERAGE_READ_SURFACE_BLOCKED_CLAIMS)
    )
    if forbidden_safe:
        raise CityOpsContractError(
            f"operator coverage read surface has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(
            f"operator coverage read surface claim overlap: {overlap}"
        )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
