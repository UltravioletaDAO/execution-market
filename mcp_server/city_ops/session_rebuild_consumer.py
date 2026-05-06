"""Read-only session rebuild consumer for City-as-a-Service proof blocks.

The closure previews proved that a rebuild surface can be described from compact
artifacts.  This module is the first real consumer: it reads the persisted proof
block JSON files from disk, validates their contracts, and emits a conservative
rebuild bundle without opening raw transcripts, unreviewed memory, or any live
sink.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .closure import FORBIDDEN_CLOSURE_SOURCES
from .contracts import CityOpsContractError
from .proof_block_artifacts import (
    DEFAULT_PROOF_ANCHOR_ID,
    PROOF_BLOCK_FILENAMES,
    _default_proof_block_dir,
)

SESSION_REBUILD_CONSUMER_SCHEMA = "city_ops.session_rebuild_consumer_bundle.v1"
SESSION_REBUILD_CONSUMER_SOURCE_ARTIFACTS = {
    "telemetry_gate": "proof_block_telemetry_gate.json",
    "session_rebuild_preview": "session_rebuild_preview.json",
    "acontext_export_preview": "acontext_export_preview.json",
}
CONSUMER_ALLOWED_SOURCES = [
    "persisted_proof_block_telemetry_gate",
    "persisted_session_rebuild_preview",
    "persisted_acontext_export_preview",
]
CONSUMER_SAFE_CLAIM = "session_rebuild_consumer_landed"


def load_session_rebuild_consumer_bundle(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load and validate a read-only rebuild bundle from persisted artifacts."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    artifacts = _load_required_artifacts(base_dir)
    telemetry_gate = artifacts["telemetry_gate"]
    session_preview = artifacts["session_rebuild_preview"]
    acontext_preview = artifacts["acontext_export_preview"]

    _assert_anchor(proof_anchor_id, telemetry_gate, session_preview, acontext_preview)
    _assert_source_contracts(session_preview, acontext_preview)
    _assert_no_forbidden_sources_needed(session_preview, acontext_preview)
    _assert_identity_parity(telemetry_gate, session_preview, acontext_preview)
    _assert_claim_limit_parity(telemetry_gate, session_preview, acontext_preview)
    _assert_boundary_parity(session_preview, acontext_preview)
    _assert_readiness_stays_bounded(telemetry_gate, session_preview, acontext_preview)

    promotion = dict(session_preview["promotion"])
    acontext_fields = acontext_preview["provenance_safe_fields"]
    safe_to_claim = list(telemetry_gate.get("safe_to_claim", []))
    consumer_safe_to_claim = [*safe_to_claim, CONSUMER_SAFE_CLAIM]

    return {
        "schema": SESSION_REBUILD_CONSUMER_SCHEMA,
        "consumer_id": f"session_rebuild_consumer:{proof_anchor_id}",
        "proof_anchor_id": proof_anchor_id,
        "coordination_session_id": telemetry_gate["coordination_session_id"],
        "compact_decision_id": telemetry_gate["compact_decision_id"],
        "review_packet_id": telemetry_gate["review_packet_id"],
        "source_artifacts": dict(SESSION_REBUILD_CONSUMER_SOURCE_ARTIFACTS),
        "source_read_contract": {
            "allowed_sources": list(CONSUMER_ALLOWED_SOURCES),
            "forbidden_sources": list(FORBIDDEN_CLOSURE_SOURCES),
            "raw_transcript_required": False,
            "read_only": True,
            "writes_live_sink": False,
        },
        "preserved_boundaries": {
            "promotion_class": promotion["promotion_class"],
            "guidance_tone": promotion["guidance_tone"],
            "guidance_placement": promotion["guidance_placement"],
            "copyable_worker_instruction": promotion["copyable_worker_instruction"],
            "behavior_change_class": telemetry_gate["behavior_change_class"],
            "summary_judgment": acontext_fields["summary_judgment"],
            "source_episode_ids": list(acontext_fields.get("source_episode_ids", [])),
        },
        "readiness": {
            "decision": dict(session_preview["readiness"]["decision"]),
            "telemetry_session_rebuild_ready": bool(
                telemetry_gate.get("session_rebuild_ready")
            ),
            "telemetry_acontext_sink_ready": bool(
                telemetry_gate.get("acontext_sink_ready")
            ),
            "consumer_promotes_readiness": False,
        },
        "safe_to_claim": consumer_safe_to_claim,
        "inherited_safe_to_claim": safe_to_claim,
        "do_not_claim_yet": list(telemetry_gate.get("do_not_claim_yet", [])),
        "next_smallest_proof": list(telemetry_gate.get("next_smallest_proof", [])),
        "consumer_verdict": "read_only_session_rebuild_consumer_landed",
    }


def _load_required_artifacts(base_dir: Path) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for key, filename in SESSION_REBUILD_CONSUMER_SOURCE_ARTIFACTS.items():
        path = base_dir / filename
        if not path.exists():
            raise CityOpsContractError(f"missing persisted proof-block artifact: {path}")
        with path.open("r", encoding="utf-8") as fh:
            artifacts[key] = json.load(fh)
    unexpected_missing = set(PROOF_BLOCK_FILENAMES) - set(artifacts)
    if unexpected_missing:
        raise CityOpsContractError(
            f"consumer artifact map missing known proof-block keys: {unexpected_missing}"
        )
    return artifacts


def _assert_anchor(
    proof_anchor_id: str,
    *artifacts: dict[str, Any],
) -> None:
    for artifact in artifacts:
        _require_equal(
            artifact.get("proof_anchor_id"),
            proof_anchor_id,
            f"{artifact.get('schema', 'artifact')}.proof_anchor_id",
        )


def _assert_source_contracts(
    session_preview: dict[str, Any],
    acontext_preview: dict[str, Any],
) -> None:
    for label, artifact in (
        ("session_rebuild_preview", session_preview),
        ("acontext_export_preview", acontext_preview),
    ):
        source_contract = _required_dict(artifact, "source_read_contract", label)
        _require_equal(
            source_contract.get("raw_transcript_required"),
            False,
            f"{label}.source_read_contract.raw_transcript_required",
        )
        forbidden_sources = source_contract.get("forbidden_sources")
        _require_equal(
            forbidden_sources,
            list(FORBIDDEN_CLOSURE_SOURCES),
            f"{label}.source_read_contract.forbidden_sources",
        )
        allowed_sources = source_contract.get("allowed_sources") or []
        for forbidden in FORBIDDEN_CLOSURE_SOURCES:
            if forbidden in allowed_sources:
                raise CityOpsContractError(
                    f"{label} cannot list forbidden source {forbidden!r} as allowed"
                )


def _assert_no_forbidden_sources_needed(
    session_preview: dict[str, Any],
    acontext_preview: dict[str, Any],
) -> None:
    """Fail if any active source contract needs a forbidden source.

    Forbidden source names are expected in explicit forbidden/excluded lists.  They
    must never appear as allowed inputs, rebuild steps, provenance refs, or any
    other active consumer dependency.
    """

    allowed_guardrail_paths = {
        ("source_read_contract", "forbidden_sources"),
        ("excluded_fields",),
    }
    for label, artifact in (
        ("session_rebuild_preview", session_preview),
        ("acontext_export_preview", acontext_preview),
    ):
        for path, value in _walk_values(artifact):
            if _path_has_allowed_guardrail_suffix(path, allowed_guardrail_paths):
                continue
            if isinstance(value, str) and value in FORBIDDEN_CLOSURE_SOURCES:
                raise CityOpsContractError(
                    f"{label} actively references forbidden source {value!r} at {'.'.join(path)}"
                )


def _assert_identity_parity(
    telemetry_gate: dict[str, Any],
    session_preview: dict[str, Any],
    acontext_preview: dict[str, Any],
) -> None:
    for key in (
        "coordination_session_id",
        "compact_decision_id",
        "review_packet_id",
        "proof_anchor_id",
    ):
        expected = telemetry_gate.get(key)
        _require_equal(session_preview.get(key), expected, f"session_rebuild_preview.{key}")
        _require_equal(acontext_preview.get(key), expected, f"acontext_export_preview.{key}")


def _assert_claim_limit_parity(
    telemetry_gate: dict[str, Any],
    session_preview: dict[str, Any],
    acontext_preview: dict[str, Any],
) -> None:
    acontext_fields = _required_dict(
        acontext_preview,
        "provenance_safe_fields",
        "acontext_export_preview",
    )
    do_not_claim = list(telemetry_gate.get("do_not_claim_yet", []))
    _require_equal(
        session_preview.get("not_safe_to_claim"),
        do_not_claim,
        "session_rebuild_preview.not_safe_to_claim",
    )
    _require_equal(
        acontext_fields.get("not_safe_to_claim"),
        do_not_claim,
        "acontext_export_preview.provenance_safe_fields.not_safe_to_claim",
    )
    _require_equal(
        session_preview.get("safe_to_claim"),
        telemetry_gate.get("safe_to_claim"),
        "session_rebuild_preview.safe_to_claim",
    )
    _require_equal(
        acontext_fields.get("safe_to_claim"),
        telemetry_gate.get("safe_to_claim"),
        "acontext_export_preview.provenance_safe_fields.safe_to_claim",
    )


def _assert_boundary_parity(
    session_preview: dict[str, Any],
    acontext_preview: dict[str, Any],
) -> None:
    promotion = _required_dict(session_preview, "promotion", "session_rebuild_preview")
    acontext_fields = _required_dict(
        acontext_preview,
        "provenance_safe_fields",
        "acontext_export_preview",
    )
    for key in (
        "promotion_class",
        "guidance_tone",
        "guidance_placement",
        "copyable_worker_instruction",
    ):
        _require_equal(
            promotion.get(key),
            acontext_fields.get(key),
            f"boundary.{key}",
        )
    copyable = _required_dict(promotion, "copyable_worker_instruction", "promotion")
    if copyable.get("allowed"):
        raise CityOpsContractError(
            "session rebuild consumer cannot strengthen cautious learning into worker-copyable instruction"
        )


def _assert_readiness_stays_bounded(
    telemetry_gate: dict[str, Any],
    session_preview: dict[str, Any],
    acontext_preview: dict[str, Any],
) -> None:
    session_readiness = _required_dict(
        session_preview,
        "readiness",
        "session_rebuild_preview",
    )
    acontext_readiness = _required_dict(
        acontext_preview,
        "readiness",
        "acontext_export_preview",
    )
    _require_equal(
        session_readiness.get("preview_promotes_readiness"),
        False,
        "session_rebuild_preview.readiness.preview_promotes_readiness",
    )
    _require_equal(
        session_readiness.get("telemetry_session_rebuild_ready"),
        bool(telemetry_gate.get("session_rebuild_ready")),
        "session_rebuild_preview.readiness.telemetry_session_rebuild_ready",
    )
    _require_equal(
        acontext_readiness.get("telemetry_acontext_sink_ready"),
        bool(telemetry_gate.get("acontext_sink_ready")),
        "acontext_export_preview.readiness.telemetry_acontext_sink_ready",
    )
    if session_preview.get("preview_verdict") == "session_rebuild_ready" and not telemetry_gate.get(
        "session_rebuild_ready"
    ):
        raise CityOpsContractError("preview cannot claim session rebuild readiness")
    if acontext_preview.get("export_status") == "acontext_sink_ready" and not telemetry_gate.get(
        "acontext_sink_ready"
    ):
        raise CityOpsContractError("preview cannot claim Acontext sink readiness")


def _walk_values(value: Any, path: tuple[str, ...] = ()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_values(child, (*path, str(key)))
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child, path)
    else:
        yield path, value


def _path_has_allowed_guardrail_suffix(
    path: tuple[str, ...],
    suffixes: set[tuple[str, ...]],
) -> bool:
    return any(path[-len(suffix) :] == suffix for suffix in suffixes)


def _required_dict(artifact: dict[str, Any], key: str, label: str) -> dict[str, Any]:
    value = artifact.get(key)
    if not isinstance(value, dict):
        raise CityOpsContractError(f"{label}.{key} must be an object")
    return value


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise CityOpsContractError(f"{label} drifted ({actual!r} != {expected!r})")
