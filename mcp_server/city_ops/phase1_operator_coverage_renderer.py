"""Read-only renderer for the persisted Phase 1 CaaS operator coverage artifact.

The renderer is intentionally thinner than an operator UI.  It consumes only
``phase1_operator_coverage_summary.json`` (or an already-loaded summary supplied
by tests), keeps safe and blocked claims adjacent per offer, and refuses to
render if any readiness flag has been promoted.  It does not read raw review
fixtures, raw transcripts, memory, Acontext transport, GPS/metadata payloads, or
freeform worker/operator context.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .phase1_operator_coverage_summary import (
    FORBIDDEN_OPERATOR_COVERAGE_SAFE_CLAIMS,
    PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME,
    PHASE1_OPERATOR_COVERAGE_SUMMARY_SCHEMA,
    load_phase1_operator_coverage_summary,
)

PHASE1_OPERATOR_COVERAGE_RENDERER_SCHEMA = "city_ops.phase1_operator_coverage_renderer.v1"
PHASE1_OPERATOR_COVERAGE_RENDERER_SAFE_CLAIM = "phase1_operator_coverage_renderer_landed"
PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME = "phase1_operator_coverage_renderer.json"

# Renderer-specific boundaries.  These are UI/read-surface guardrails, not new
# readiness categories.  They stay blocked even after the renderer lands.
PHASE1_OPERATOR_COVERAGE_RENDERER_BLOCKED_CLAIMS = [
    "customer_copy_ready",
    "operator_ui_ready",
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
    "polished_operator_console_ready",
    "customer_visible_catalog_ready",
    "worker_instruction_surface_ready",
]

_RENDERER_FORBIDDEN_INPUTS = [
    "raw_transcript",
    "raw_review_fixture",
    "unreviewed_memory",
    "freeform_worker_chat",
    "private_operator_context",
    "live_acontext_transport",
    "gps_or_metadata_payloads",
]

_RENDERER_FALSE_FLAGS = [
    "writes_customer_copy",
    "writes_municipal_memory",
    "writes_live_acontext",
    "enables_dispatch_automation",
    "publishes_worker_doctrine",
    "semantic_reinterpretation_performed",
    "reads_raw_review_fixtures",
    "reads_raw_transcripts",
]


def build_phase1_operator_coverage_renderer(
    *,
    fixture_dir: str | Path | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a data-only renderer payload from the persisted summary artifact.

    The default path deliberately goes through ``load_phase1_operator_coverage_summary``
    so the source artifact is validated before rendering.  Tests may pass an
    already-loaded summary to verify rejection behavior, but it is still checked
    with renderer-local conservative assertions.
    """

    source_summary = summary or load_phase1_operator_coverage_summary(
        fixture_dir=fixture_dir
    )
    _assert_summary_renderable(source_summary)

    safe_to_claim = _dedupe(
        [
            *source_summary["claim_boundaries"]["safe_to_claim"],
            PHASE1_OPERATOR_COVERAGE_RENDERER_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_summary["claim_boundaries"]["do_not_claim_yet"],
            *PHASE1_OPERATOR_COVERAGE_RENDERER_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    rows = [_render_offer_row(row) for row in source_summary["coverage_by_offer"]]

    renderer = {
        "schema": PHASE1_OPERATOR_COVERAGE_RENDERER_SCHEMA,
        "renderer_id": f"operator_coverage_renderer:{source_summary['summary_id']}",
        "source_summary_id": source_summary["summary_id"],
        "source_registry_id": source_summary["source_registry_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME],
            "consumes_only": [PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME],
            "forbidden_inputs": list(_RENDERER_FORBIDDEN_INPUTS),
            "writes_customer_copy": False,
            "writes_municipal_memory": False,
            "writes_live_acontext": False,
            "enables_dispatch_automation": False,
            "publishes_worker_doctrine": False,
            "semantic_reinterpretation_performed": False,
            "reads_raw_review_fixtures": False,
            "reads_raw_transcripts": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "coverage_totals": dict(source_summary["coverage_totals"]),
        "readiness": {
            "renderer_promotes_readiness": False,
            "customer_copy_ready": False,
            "operator_ui_ready": False,
            "dispatch_automation_ready": False,
            "live_acontext_ready": False,
            "erc8004_reputation_ready": False,
            "worker_skill_dna_ready": False,
            "legal_or_regulator_ready": False,
            "gps_or_metadata_exposure_allowed": False,
            "worker_copyable_municipal_doctrine_ready": False,
        },
        "coverage_table": rows,
        "display_lines": [_display_line(row) for row in rows],
        "renderer_verdict": "phase1_operator_coverage_renderer_landed_read_only_not_customer_ready",
        "next_smallest_proof": (
            "Mount this renderer behind an internal/admin-only read surface that uses this payload as-is. "
            "Do not add customer copy, dispatch routing, live Acontext writes, reputation updates, "
            "worker Skill DNA, legal/regulator claims, GPS/metadata exposure, or worker-copyable doctrine."
        ),
    }
    _assert_renderer_is_conservative(renderer)
    return renderer


def write_phase1_operator_coverage_renderer(
    *, fixture_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic renderer payload beside the summary artifact."""

    renderer = build_phase1_operator_coverage_renderer(fixture_dir=fixture_dir)
    base_dir = _operator_coverage_renderer_dir(fixture_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME
    path.write_text(json.dumps(renderer, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_phase1_operator_coverage_renderer(
    *, fixture_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted renderer payload."""

    path = _operator_coverage_renderer_dir(fixture_dir) / PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME
    with path.open("r", encoding="utf-8") as fh:
        renderer = json.load(fh)
    if not isinstance(renderer, dict):
        raise CityOpsContractError("operator coverage renderer artifact must be a JSON object")
    _assert_renderer_is_conservative(renderer)
    return renderer


def _operator_coverage_renderer_dir(fixture_dir: str | Path | None = None) -> Path:
    if fixture_dir is not None:
        return Path(fixture_dir)
    # The summary loader owns the canonical default path.  Reuse the summary file
    # location by resolving through the existing loader's default artifact path.
    from .phase1_review_output_schemas import OFFER_SPEC_DIR

    return OFFER_SPEC_DIR / "reviewed_outputs"


def _render_offer_row(row: dict[str, Any]) -> dict[str, Any]:
    claims = row.get("claims", {})
    safe_to_claim = list(claims.get("safe_to_claim", []))
    do_not_claim_yet = list(claims.get("do_not_claim_yet", []))
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    promoted_readiness = dict(row.get("promoted_readiness", {}))
    promoted = [flag for flag, value in promoted_readiness.items() if value is True]
    if promoted:
        raise CityOpsContractError(
            f"operator coverage renderer refuses promoted row readiness: {promoted}"
        )

    return {
        "offer_id": row["offer_id"],
        "fixture_id": row["fixture_id"],
        "source_file": row["source_file"],
        "outcome_status": row["outcome_status"],
        "source_type": row["source_type"],
        "follow_on_task_trigger": row["follow_on_task_trigger"],
        "proof_status_label": row["proof_status_label"],
        "safe_to_claim": safe_to_claim,
        "do_not_claim_yet": do_not_claim_yet,
        "readiness_promoted": False,
    }


def _display_line(row: dict[str, Any]) -> str:
    safe = ", ".join(row["safe_to_claim"])
    blocked = ", ".join(row["do_not_claim_yet"])
    return (
        f"{row['offer_id']} | fixture={row['fixture_id']} | "
        f"outcome={row['outcome_status']} | source_type={row['source_type']} | "
        f"next={row['follow_on_task_trigger']} | safe=[{safe}] | blocked=[{blocked}]"
    )


def _assert_summary_renderable(summary: dict[str, Any]) -> None:
    if summary.get("schema") != PHASE1_OPERATOR_COVERAGE_SUMMARY_SCHEMA:
        raise CityOpsContractError("operator coverage renderer expected summary schema")
    derived_from = summary.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("operator coverage renderer requires read-only summary")
    for flag in [
        "writes_customer_copy",
        "writes_municipal_memory",
        "writes_live_acontext",
        "enables_dispatch_automation",
        "publishes_worker_doctrine",
    ]:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(
                f"operator coverage renderer rejects source overclaim: {flag}"
            )

    readiness = summary.get("readiness", {})
    promoted = [flag for flag, value in readiness.items() if value is True]
    if promoted:
        raise CityOpsContractError(
            f"operator coverage renderer refuses promoted summary readiness: {promoted}"
        )

    boundaries = summary.get("claim_boundaries", {})
    _assert_claim_boundaries(
        list(boundaries.get("safe_to_claim", [])),
        list(boundaries.get("do_not_claim_yet", [])),
    )

    rows = summary.get("coverage_by_offer")
    if not isinstance(rows, list) or not rows:
        raise CityOpsContractError("operator coverage renderer requires coverage rows")
    if summary.get("coverage_totals", {}).get("reviewed_fixture_count") != len(rows):
        raise CityOpsContractError("operator coverage renderer fixture count drift")


def _assert_renderer_is_conservative(renderer: dict[str, Any]) -> None:
    if renderer.get("schema") != PHASE1_OPERATOR_COVERAGE_RENDERER_SCHEMA:
        raise CityOpsContractError("operator coverage renderer schema mismatch")
    derived_from = renderer.get("derived_from", {})
    if derived_from.get("read_only") is not True:
        raise CityOpsContractError("operator coverage renderer must stay read-only")
    if derived_from.get("consumes_only") != [PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME]:
        raise CityOpsContractError("operator coverage renderer must consume only summary artifact")
    for flag in _RENDERER_FALSE_FLAGS:
        if derived_from.get(flag) is not False:
            raise CityOpsContractError(f"operator coverage renderer overclaims {flag}")

    boundaries = renderer.get("claim_boundaries", {})
    _assert_claim_boundaries(
        list(boundaries.get("safe_to_claim", [])),
        list(boundaries.get("do_not_claim_yet", [])),
    )
    blocked = set(boundaries["do_not_claim_yet"])
    missing_blocked = [
        claim for claim in PHASE1_OPERATOR_COVERAGE_RENDERER_BLOCKED_CLAIMS if claim not in blocked
    ]
    if missing_blocked:
        raise CityOpsContractError(
            f"operator coverage renderer missing blocked claims: {missing_blocked}"
        )

    readiness = renderer.get("readiness", {})
    promoted = [flag for flag, value in readiness.items() if value is True]
    if promoted:
        raise CityOpsContractError(
            f"operator coverage renderer promoted readiness: {promoted}"
        )

    for row in renderer.get("coverage_table", []):
        if row.get("readiness_promoted") is not False:
            raise CityOpsContractError("operator coverage renderer row promoted readiness")
        _assert_claim_boundaries(
            list(row.get("safe_to_claim", [])),
            list(row.get("do_not_claim_yet", [])),
        )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    if not safe_to_claim:
        raise CityOpsContractError("operator coverage renderer missing safe_to_claim")
    if not do_not_claim_yet:
        raise CityOpsContractError("operator coverage renderer missing do_not_claim_yet")
    forbidden_safe = sorted(
        set(safe_to_claim) & set(FORBIDDEN_OPERATOR_COVERAGE_SAFE_CLAIMS)
    )
    if forbidden_safe:
        raise CityOpsContractError(
            f"operator coverage renderer has forbidden safe claims: {forbidden_safe}"
        )
    overlap = sorted(set(safe_to_claim) & set(do_not_claim_yet))
    if overlap:
        raise CityOpsContractError(f"operator coverage renderer claim overlap: {overlap}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
