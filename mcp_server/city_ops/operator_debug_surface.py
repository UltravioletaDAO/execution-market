"""Thin operator/debug surface for City-as-a-Service proof blocks.

This module deliberately builds a data-only inspection surface over the already
persisted CaaS proof artifacts.  It does not create a polished dashboard, does
not read raw transcripts, and does not promote Acontext or session rebuild
readiness.  Its job is to make the current conservative state inspectable
without softening the claim boundaries.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .acontext_live_preflight import ACONTEXT_LIVE_PREFLIGHT_SAFE_CLAIM
from .acontext_transport import ACONTEXT_TRANSPORT_SAFE_CLAIM
from .contracts import CityOpsContractError
from .proof_block_artifacts import DEFAULT_PROOF_ANCHOR_ID, _default_proof_block_dir
from .session_rebuild_consumer import REPORT_SAFE_CLAIM

OPERATOR_DEBUG_SURFACE_SCHEMA = "city_ops.operator_debug_surface.v1"
OPERATOR_DEBUG_SURFACE_SAFE_CLAIM = "thin_operator_debug_surface_landed"
OPERATOR_DEBUG_SURFACE_BLOCKED_CLAIMS = [
    "closure_proof_landed",
    "session_rebuild_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "acontext_live_write_completed",
    "acontext_live_retrieval_completed",
    "acontext_live_transport_parity_landed",
    "worker-copyable municipal doctrine",
    "polished_review_console_ready",
    "office_memory_view_ready",
    "broad_operator_workflow_ready",
]


def build_operator_debug_surface(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
    session_rebuild_report: dict[str, Any] | None = None,
    acontext_transport_parity_result: dict[str, Any] | None = None,
    acontext_live_preflight_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only debug surface over persisted CaaS proof artifacts.

    The returned artifact is intentionally small and mechanical.  It can answer
    what was proved, what is still unsafe to claim, where operator guidance may
    appear, and why live Acontext transport remains blocked.  It cannot hide or
    reword the inherited ``do_not_claim_yet`` boundaries.
    """

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    report = session_rebuild_report or _load_json(base_dir / "session_rebuild_report.json")
    parity = acontext_transport_parity_result or _load_json(
        base_dir / "acontext_transport_parity_result.json"
    )
    preflight = acontext_live_preflight_result or _load_json(
        base_dir / "acontext_live_preflight_result.json"
    )
    _assert_surface_inputs(proof_anchor_id, report, parity, preflight)

    safe_to_claim = _dedupe(
        [
            *preflight["claim_boundaries"].get("safe_to_claim", []),
            REPORT_SAFE_CLAIM,
            ACONTEXT_TRANSPORT_SAFE_CLAIM,
            ACONTEXT_LIVE_PREFLIGHT_SAFE_CLAIM,
            OPERATOR_DEBUG_SURFACE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *report["claim_boundaries"].get("do_not_claim_yet", []),
            *parity["claim_boundaries"].get("do_not_claim_yet", []),
            *preflight["claim_boundaries"].get("do_not_claim_yet", []),
            *OPERATOR_DEBUG_SURFACE_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_blocked_claims_safe(safe_to_claim)
    _assert_do_not_claim_preserved(report, parity, preflight, do_not_claim_yet)

    identity = dict(report["identity"])
    promotion = report["promotion_boundaries"]
    readiness = _surface_readiness(report, parity, preflight)
    cards = _surface_cards(report, parity, preflight, readiness, safe_to_claim, do_not_claim_yet)

    return {
        "schema": OPERATOR_DEBUG_SURFACE_SCHEMA,
        "surface_id": f"operator_debug_surface:{proof_anchor_id}",
        "proof_anchor_id": proof_anchor_id,
        "coordination_session_id": identity["coordination_session_id"],
        "compact_decision_id": identity["compact_decision_id"],
        "review_packet_id": identity["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": [
                "session_rebuild_report.json",
                "acontext_transport_parity_result.json",
                "acontext_live_preflight_result.json",
            ],
            "forbidden_sources": [
                "raw_transcript",
                "unreviewed_memory",
                "freeform_worker_chat",
                "private_operator_context",
            ],
            "writes_live_sink": False,
            "semantic_reinterpretation_performed": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_visibility": {
            "guidance_placement": promotion["guidance_placement"],
            "guidance_tone": promotion["guidance_tone"],
            "summary_judgment": promotion["summary_judgment"],
            "copyable_worker_instruction": promotion["copyable_worker_instruction"],
            "worker_copyable_surface_enabled": False,
        },
        "readiness": readiness,
        "debug_cards": cards,
        "surface_verdict": _surface_verdict(readiness),
        "next_smallest_proof": list(preflight["next_smallest_proof"]),
    }


def write_operator_debug_surface_fixture(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic operator/debug surface fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    surface = build_operator_debug_surface(proof_anchor_id, artifact_dir=base_dir)
    path = base_dir / "operator_debug_surface.json"
    path.write_text(json.dumps(surface, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _surface_readiness(
    report: dict[str, Any], parity: dict[str, Any], preflight: dict[str, Any]
) -> dict[str, Any]:
    preflight_readiness = preflight["readiness"]
    return {
        "surface_promotes_readiness": False,
        "session_rebuild_ready": False,
        "acontext_sink_ready": False,
        "runtime_parity_proven": False,
        "live_acontext_write_performed": bool(
            preflight_readiness.get("live_acontext_write_performed")
        ),
        "live_acontext_retrieval_performed": bool(
            preflight_readiness.get("live_acontext_retrieval_performed")
        ),
        "ready_to_attempt_live_transport": bool(
            preflight_readiness.get("ready_to_attempt_live_transport")
        ),
        "local_transport_parity_fixture_passed": all(
            check.get("status") == "passed" for check in parity.get("parity_checks", [])
        ),
        "read_only_report_available": report.get("schema")
        == "city_ops.session_rebuild_report.v1",
        "blockers": list(preflight_readiness.get("blockers", [])),
    }


def _surface_cards(
    report: dict[str, Any],
    parity: dict[str, Any],
    preflight: dict[str, Any],
    readiness: dict[str, Any],
    safe_to_claim: list[str],
    do_not_claim_yet: list[str],
) -> list[dict[str, Any]]:
    return [
        {
            "card": "identity",
            "status": "preserved",
            "values": dict(report["identity"]),
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
            "card": "operator_guidance",
            "status": "operator_visible_not_worker_copyable",
            "values": {
                "guidance_placement": report["promotion_boundaries"]["guidance_placement"],
                "guidance_tone": report["promotion_boundaries"]["guidance_tone"],
                "copyable_worker_instruction": report["promotion_boundaries"][
                    "copyable_worker_instruction"
                ],
            },
        },
        {
            "card": "transport",
            "status": (
                "ready_to_attempt_live_transport"
                if readiness["ready_to_attempt_live_transport"]
                else "blocked_before_live_sink_write"
            ),
            "values": {
                "local_parity_result": parity["result_verdict"],
                "preflight_verdict": preflight["preflight_verdict"],
                "blockers": readiness["blockers"],
            },
        },
    ]


def _surface_verdict(readiness: dict[str, Any]) -> str:
    if readiness["ready_to_attempt_live_transport"]:
        return "thin_operator_debug_surface_landed_live_transport_attemptable"
    return "thin_operator_debug_surface_landed_live_transport_blocked"


def _assert_surface_inputs(
    proof_anchor_id: str,
    report: dict[str, Any],
    parity: dict[str, Any],
    preflight: dict[str, Any],
) -> None:
    expected = {
        "report": "city_ops.session_rebuild_report.v1",
        "parity": "city_ops.acontext_transport_parity_result.v1",
        "preflight": "city_ops.acontext_live_preflight.v1",
    }
    actual = {
        "report": report.get("schema"),
        "parity": parity.get("schema"),
        "preflight": preflight.get("schema"),
    }
    for name, schema in expected.items():
        if actual[name] != schema:
            raise CityOpsContractError(f"Operator debug surface expected {name} schema {schema}")

    identities = [
        report.get("identity"),
        parity.get("identity"),
        {
            "proof_anchor_id": preflight.get("proof_anchor_id"),
            "coordination_session_id": preflight.get("coordination_session_id"),
            "compact_decision_id": preflight.get("compact_decision_id"),
            "review_packet_id": preflight.get("review_packet_id"),
        },
    ]
    for identity in identities:
        if identity.get("proof_anchor_id") != proof_anchor_id:
            raise CityOpsContractError("Operator debug surface proof anchor drift")
    if identities[0] != identities[1] or identities[0] != identities[2]:
        raise CityOpsContractError("Operator debug surface identity drift across artifacts")

    copyable = report["promotion_boundaries"]["copyable_worker_instruction"]
    if copyable.get("allowed") is not False:
        raise CityOpsContractError("Operator debug surface cannot enable worker-copyable guidance")
    if preflight["probe"].get("live_acontext_write_performed") is not False:
        raise CityOpsContractError("Operator debug surface cannot consume live-write preflight probe")
    if preflight["probe"].get("live_acontext_retrieval_performed") is not False:
        raise CityOpsContractError("Operator debug surface cannot consume live-retrieval preflight probe")


def _assert_no_blocked_claims_safe(safe_to_claim: list[str]) -> None:
    blocked = sorted(set(safe_to_claim).intersection(OPERATOR_DEBUG_SURFACE_BLOCKED_CLAIMS))
    if blocked:
        raise CityOpsContractError(
            f"Operator debug surface cannot mark blocked claims safe: {blocked}"
        )


def _assert_do_not_claim_preserved(
    report: dict[str, Any],
    parity: dict[str, Any],
    preflight: dict[str, Any],
    do_not_claim_yet: list[str],
) -> None:
    missing: list[str] = []
    for source in (report, parity, preflight):
        for claim in source["claim_boundaries"].get("do_not_claim_yet", []):
            if claim not in do_not_claim_yet:
                missing.append(claim)
    if missing:
        raise CityOpsContractError(
            f"Operator debug surface softened blocked claims: {sorted(set(missing))}"
        )


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
