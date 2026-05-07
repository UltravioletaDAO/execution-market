"""Acontext transport parity fixture for City-as-a-Service proof blocks.

The rebuild report fixture made the compact proof block inspectable without
reopening raw transcripts or unreviewed memory.  This module takes the next
small step: package that report as the exact payload a future Acontext sink
should write/retrieve, then prove the round trip preserves identity, claims,
promotion boundaries, copyability, and readiness without semantic
reinterpretation.

This is intentionally not a live Acontext client.  Until Docker/local Acontext
is available, it models the transport contract as a deterministic local fixture
and keeps ``acontext_sink_ready`` false.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .proof_block_artifacts import DEFAULT_PROOF_ANCHOR_ID, _default_proof_block_dir
from .session_rebuild_consumer import (
    REPORT_BLOCKED_CLAIMS,
    SESSION_REBUILD_REPORT_SCHEMA,
    build_session_rebuild_report,
)

ACONTEXT_TRANSPORT_PACKET_SCHEMA = "city_ops.acontext_transport_packet.v1"
ACONTEXT_TRANSPORT_RETRIEVAL_SCHEMA = "city_ops.acontext_transport_retrieval.v1"
ACONTEXT_TRANSPORT_PARITY_RESULT_SCHEMA = "city_ops.acontext_transport_parity_result.v1"
ACONTEXT_TRANSPORT_SAFE_CLAIM = "acontext_transport_parity_test_landed"
ACONTEXT_TRANSPORT_BLOCKED_CLAIMS = [
    *REPORT_BLOCKED_CLAIMS,
    "closure_proof_ready",
    "runtime_parity_proven",
]


def build_acontext_transport_packet(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
    report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the exact compact payload for a future Acontext write.

    The packet is derived from ``city_ops.session_rebuild_report.v1`` only.  It
    is a local parity fixture, not a live sink write, so it must not claim
    Acontext readiness or invent any stronger worker/operator guidance.
    """

    source_report = report or build_session_rebuild_report(
        proof_anchor_id,
        artifact_dir=artifact_dir,
    )
    _assert_report_contract(source_report)

    identity = dict(source_report["identity"])
    return {
        "schema": ACONTEXT_TRANSPORT_PACKET_SCHEMA,
        "packet_id": f"acontext_transport_packet:{identity['proof_anchor_id']}",
        "proof_anchor_id": identity["proof_anchor_id"],
        "coordination_session_id": identity["coordination_session_id"],
        "compact_decision_id": identity["compact_decision_id"],
        "review_packet_id": identity["review_packet_id"],
        "namespace": "execution_market.city_as_a_service",
        "source_report": {
            "schema": source_report["schema"],
            "report_id": source_report["report_id"],
            "report_verdict": source_report["report_verdict"],
        },
        "transport_contract": {
            "intended_sink": "acontext",
            "transport_mode": "local_parity_fixture",
            "live_acontext_write_performed": False,
            "semantic_reinterpretation_performed": False,
            "derives_from_session_rebuild_report_only": True,
            "raw_transcript_required": False,
            "writes_live_sink": False,
            "ready_to_replace_local_sink": False,
        },
        "stored_payload": {
            "identity": identity,
            "claim_boundaries": dict(source_report["claim_boundaries"]),
            "promotion_boundaries": dict(source_report["promotion_boundaries"]),
            "readiness": dict(source_report["readiness"]),
        },
        "retrieval_contract": {
            "must_preserve": [
                "proof_anchor_id",
                "coordination_session_id",
                "compact_decision_id",
                "review_packet_id",
                "safe_to_claim",
                "do_not_claim_yet",
                "promotion_class",
                "guidance_tone",
                "guidance_placement",
                "copyable_worker_instruction",
                "readiness",
            ],
            "cannot_mark_safe": list(ACONTEXT_TRANSPORT_BLOCKED_CLAIMS),
            "cannot_make_worker_copyable": True,
            "cannot_promote_readiness": True,
        },
    }


def retrieve_acontext_transport_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Return the local retrieval view for a transport packet.

    A future live Acontext adapter should make this function boring to replace:
    write the same ``stored_payload`` into Acontext and retrieve the same fields
    back without changing their meaning.
    """

    _assert_packet_contract(packet)
    return {
        "schema": ACONTEXT_TRANSPORT_RETRIEVAL_SCHEMA,
        "retrieval_id": f"acontext_transport_retrieval:{packet['proof_anchor_id']}",
        "packet_id": packet["packet_id"],
        "proof_anchor_id": packet["proof_anchor_id"],
        "transport_mode": packet["transport_contract"]["transport_mode"],
        "live_acontext_retrieval_performed": False,
        "semantic_reinterpretation_performed": False,
        "retrieved_payload": dict(packet["stored_payload"]),
    }


def assert_acontext_transport_parity(
    packet: dict[str, Any],
    retrieval: dict[str, Any],
) -> None:
    """Fail if transport retrieval strengthens or drifts from the write packet."""

    _assert_packet_contract(packet)
    _assert_retrieval_contract(retrieval)
    _require_equal(
        retrieval.get("packet_id"),
        packet.get("packet_id"),
        "acontext_transport_retrieval.packet_id",
    )
    _require_equal(
        retrieval.get("proof_anchor_id"),
        packet.get("proof_anchor_id"),
        "acontext_transport_retrieval.proof_anchor_id",
    )
    _require_equal(
        retrieval.get("semantic_reinterpretation_performed"),
        False,
        "acontext_transport_retrieval.semantic_reinterpretation_performed",
    )

    retrieved_payload = _required_dict(
        retrieval,
        "retrieved_payload",
        "acontext_transport_retrieval",
    )
    stored_payload = _required_dict(packet, "stored_payload", "acontext_transport_packet")
    for key in ("identity", "claim_boundaries", "promotion_boundaries", "readiness"):
        _require_equal(
            retrieved_payload.get(key),
            stored_payload.get(key),
            f"acontext_transport.{key}",
        )

    _assert_payload_boundaries(retrieved_payload)


def build_acontext_transport_parity_result(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
    report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic Acontext transport parity result fixture."""

    packet = build_acontext_transport_packet(
        proof_anchor_id,
        artifact_dir=artifact_dir,
        report=report,
    )
    retrieval = retrieve_acontext_transport_packet(packet)
    assert_acontext_transport_parity(packet, retrieval)

    payload = packet["stored_payload"]
    claim_boundaries = payload["claim_boundaries"]
    safe_to_claim = _dedupe(
        [*claim_boundaries.get("safe_to_claim", []), ACONTEXT_TRANSPORT_SAFE_CLAIM]
    )
    do_not_claim_yet = _dedupe(
        [
            *claim_boundaries.get("do_not_claim_yet", []),
            *ACONTEXT_TRANSPORT_BLOCKED_CLAIMS,
        ]
    )
    for blocked_claim in ACONTEXT_TRANSPORT_BLOCKED_CLAIMS:
        if blocked_claim in safe_to_claim:
            raise CityOpsContractError(
                "Acontext transport parity cannot mark blocked claim safe: "
                f"{blocked_claim!r}"
            )

    return {
        "schema": ACONTEXT_TRANSPORT_PARITY_RESULT_SCHEMA,
        "result_id": f"acontext_transport_parity:{packet['proof_anchor_id']}",
        "proof_anchor_id": packet["proof_anchor_id"],
        "coordination_session_id": packet["coordination_session_id"],
        "compact_decision_id": packet["compact_decision_id"],
        "review_packet_id": packet["review_packet_id"],
        "source_report": dict(packet["source_report"]),
        "packet_id": packet["packet_id"],
        "retrieval_id": retrieval["retrieval_id"],
        "identity": dict(payload["identity"]),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "inherited_safe_to_claim": list(claim_boundaries.get("safe_to_claim", [])),
            "do_not_claim_yet": do_not_claim_yet,
        },
        "promotion_boundaries": dict(payload["promotion_boundaries"]),
        "readiness": dict(payload["readiness"]),
        "transport_contract": dict(packet["transport_contract"]),
        "parity_checks": [
            {"check": "identity", "status": "passed"},
            {"check": "claim_boundaries", "status": "passed"},
            {"check": "promotion_boundaries", "status": "passed"},
            {"check": "readiness", "status": "passed"},
            {"check": "worker_copyability", "status": "passed"},
        ],
        "result_verdict": "acontext_transport_parity_fixture_landed",
        "next_smallest_proof": [
            "run this same packet through a live local Acontext server once Docker is available",
            "prove live retrieval preserves the same identity, claim, promotion, copyability, and readiness boundaries",
            "keep acontext_sink_ready=false until the live sink path passes without semantic strengthening",
        ],
    }


def write_acontext_transport_parity_fixture(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
) -> Path:
    """Write the deterministic local Acontext transport parity fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    result = build_acontext_transport_parity_result(
        proof_anchor_id,
        artifact_dir=base_dir,
    )
    path = base_dir / "acontext_transport_parity_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _assert_report_contract(report: dict[str, Any]) -> None:
    _require_equal(
        report.get("schema"),
        SESSION_REBUILD_REPORT_SCHEMA,
        "acontext_transport.source_report.schema",
    )
    for key in (
        "report_id",
        "report_verdict",
        "identity",
        "claim_boundaries",
        "promotion_boundaries",
        "readiness",
        "source_read_contract",
    ):
        if key not in report:
            raise CityOpsContractError(f"Acontext transport source report missing {key}")
    source_contract = _required_dict(
        report,
        "source_read_contract",
        "acontext_transport.source_report",
    )
    _require_equal(
        source_contract.get("raw_transcript_required"),
        False,
        "acontext_transport.source_report.raw_transcript_required",
    )
    _require_equal(
        source_contract.get("writes_live_sink"),
        False,
        "acontext_transport.source_report.writes_live_sink",
    )
    _assert_payload_boundaries(
        {
            "identity": report["identity"],
            "claim_boundaries": report["claim_boundaries"],
            "promotion_boundaries": report["promotion_boundaries"],
            "readiness": report["readiness"],
        }
    )


def _assert_packet_contract(packet: dict[str, Any]) -> None:
    _require_equal(
        packet.get("schema"),
        ACONTEXT_TRANSPORT_PACKET_SCHEMA,
        "acontext_transport_packet.schema",
    )
    for key in (
        "packet_id",
        "proof_anchor_id",
        "source_report",
        "transport_contract",
        "stored_payload",
        "retrieval_contract",
    ):
        if key not in packet:
            raise CityOpsContractError(f"Acontext transport packet missing {key}")
    transport_contract = _required_dict(
        packet,
        "transport_contract",
        "acontext_transport_packet",
    )
    _require_equal(
        transport_contract.get("semantic_reinterpretation_performed"),
        False,
        "acontext_transport_packet.semantic_reinterpretation_performed",
    )
    _require_equal(
        transport_contract.get("live_acontext_write_performed"),
        False,
        "acontext_transport_packet.live_acontext_write_performed",
    )
    _require_equal(
        transport_contract.get("writes_live_sink"),
        False,
        "acontext_transport_packet.writes_live_sink",
    )
    _require_equal(
        transport_contract.get("ready_to_replace_local_sink"),
        False,
        "acontext_transport_packet.ready_to_replace_local_sink",
    )
    _assert_payload_boundaries(
        _required_dict(packet, "stored_payload", "acontext_transport_packet")
    )


def _assert_retrieval_contract(retrieval: dict[str, Any]) -> None:
    _require_equal(
        retrieval.get("schema"),
        ACONTEXT_TRANSPORT_RETRIEVAL_SCHEMA,
        "acontext_transport_retrieval.schema",
    )
    _require_equal(
        retrieval.get("live_acontext_retrieval_performed"),
        False,
        "acontext_transport_retrieval.live_acontext_retrieval_performed",
    )


def _assert_payload_boundaries(payload: dict[str, Any]) -> None:
    claims = _required_dict(payload, "claim_boundaries", "acontext_transport_payload")
    safe_to_claim = set(claims.get("safe_to_claim") or [])
    blocked_safe_claims = safe_to_claim.intersection(ACONTEXT_TRANSPORT_BLOCKED_CLAIMS)
    if blocked_safe_claims:
        raise CityOpsContractError(
            "Acontext transport cannot mark blocked claims safe: "
            f"{sorted(blocked_safe_claims)}"
        )

    promotion = _required_dict(
        payload,
        "promotion_boundaries",
        "acontext_transport_payload",
    )
    copyable = _required_dict(
        promotion,
        "copyable_worker_instruction",
        "acontext_transport_payload.promotion_boundaries",
    )
    _require_equal(
        copyable.get("allowed"),
        False,
        "acontext_transport.copyable_worker_instruction.allowed",
    )

    readiness = _required_dict(payload, "readiness", "acontext_transport_payload")
    decision = _required_dict(readiness, "decision", "acontext_transport_payload.readiness")
    _require_equal(
        decision.get("session_rebuild_ready"),
        False,
        "acontext_transport.readiness.decision.session_rebuild_ready",
    )
    _require_equal(
        decision.get("export_ready"),
        False,
        "acontext_transport.readiness.decision.export_ready",
    )
    _require_equal(
        readiness.get("telemetry_acontext_sink_ready"),
        False,
        "acontext_transport.readiness.telemetry_acontext_sink_ready",
    )
    _require_equal(
        readiness.get("telemetry_session_rebuild_ready"),
        False,
        "acontext_transport.readiness.telemetry_session_rebuild_ready",
    )
    _require_equal(
        readiness.get("consumer_promotes_readiness"),
        False,
        "acontext_transport.readiness.consumer_promotes_readiness",
    )
    _require_equal(
        readiness.get("report_promotes_readiness"),
        False,
        "acontext_transport.readiness.report_promotes_readiness",
    )


def _required_dict(artifact: dict[str, Any], key: str, label: str) -> dict[str, Any]:
    value = artifact.get(key)
    if not isinstance(value, dict):
        raise CityOpsContractError(f"{label}.{key} must be an object")
    return value


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise CityOpsContractError(f"{label} drifted ({actual!r} != {expected!r})")


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
