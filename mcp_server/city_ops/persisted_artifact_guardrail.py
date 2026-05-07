"""Guardrails over persisted City-as-a-Service proof artifacts.

This module is intentionally narrow.  It does not build a new product surface,
call live Acontext, or reinterpret municipal evidence.  It checks the already
persisted proof-block artifacts and fails if a later consumer drops blocked
claims, overclaims readiness, reintroduces raw-source dependence, or drifts into
worker-copyable municipal doctrine before the proof ladder earns it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .proof_block_artifacts import DEFAULT_PROOF_ANCHOR_ID, _default_proof_block_dir

PERSISTED_ARTIFACT_GUARDRAIL_SCHEMA = "city_ops.persisted_artifact_guardrail.v1"
PERSISTED_ARTIFACT_GUARDRAIL_SAFE_CLAIM = "persisted_artifact_guardrail_landed"

GUARDRAIL_SOURCE_ARTIFACTS = [
    "operator_debug_surface.json",
    "proof_observability_snapshot.json",
    "coordination_intelligence_snapshot.json",
]

REQUIRED_BLOCKED_CLAIMS = [
    "closure_proof_landed",
    "session_rebuild_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "acontext_live_write_completed",
    "acontext_live_retrieval_completed",
    "acontext_live_transport_parity_landed",
    "worker-copyable municipal doctrine",
]

READINESS_FLAGS_THAT_MUST_REMAIN_FALSE = [
    "session_rebuild_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "live_acontext_write_performed",
    "live_acontext_retrieval_performed",
    "worker_copyable_doctrine_ready",
]

FORBIDDEN_RAW_SOURCES = [
    "raw_transcript",
    "raw_transcripts",
    "unreviewed_memory",
    "unreviewed_worker_uploads",
    "freeform_worker_chat",
    "freeform_chat_as_authority",
    "private_operator_context",
]
REQUIRED_FORBIDDEN_SOURCE_DECLARATIONS = [
    "raw_transcript",
    "unreviewed_memory",
    "freeform_worker_chat",
    "private_operator_context",
]

FORBIDDEN_SAFE_CLAIMS = [
    *REQUIRED_BLOCKED_CLAIMS,
    "closure_proof_ready",
    "worker_copyable_doctrine_ready",
    "worker-copyable doctrine",
]


def build_persisted_artifact_guardrail_report(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
    artifacts: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate conservative invariants across persisted proof artifacts.

    The checked artifacts are the latest consumer-facing proof surfaces.  They
    must keep every critical blocked claim visible, keep critical readiness
    claims false, stay read-only over reviewed artifacts, and keep the current
    municipal learning operator-visible but not worker-copyable.
    """

    source_artifacts = artifacts or _load_guardrail_artifacts(artifact_dir)
    _assert_expected_artifacts(source_artifacts)

    checks = [
        _check_blocked_claims_preserved(source_artifacts),
        _check_readiness_honesty(source_artifacts),
        _check_raw_source_independence(source_artifacts),
        _check_worker_copyability_boundary(source_artifacts),
    ]

    failed = [check for check in checks if check["status"] != "passed"]
    if failed:
        raise CityOpsContractError(
            "Persisted artifact guardrail failed: "
            + "; ".join(f"{check['check']}={check['status']}" for check in failed)
        )

    safe_to_claim = _dedupe(
        [
            *source_artifacts["coordination_intelligence_snapshot.json"][
                "claim_boundaries"
            ].get("safe_to_claim", []),
            PERSISTED_ARTIFACT_GUARDRAIL_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source_artifacts["coordination_intelligence_snapshot.json"][
                "claim_boundaries"
            ].get("do_not_claim_yet", []),
            *REQUIRED_BLOCKED_CLAIMS,
        ]
    )
    _assert_no_forbidden_safe_claims(safe_to_claim)

    return {
        "schema": PERSISTED_ARTIFACT_GUARDRAIL_SCHEMA,
        "guardrail_id": f"persisted_artifact_guardrail:{proof_anchor_id}",
        "proof_anchor_id": proof_anchor_id,
        "coordination_session_id": source_artifacts[
            "coordination_intelligence_snapshot.json"
        ]["coordination_session_id"],
        "compact_decision_id": source_artifacts[
            "coordination_intelligence_snapshot.json"
        ]["compact_decision_id"],
        "review_packet_id": source_artifacts["coordination_intelligence_snapshot.json"][
            "review_packet_id"
        ],
        "derived_from": {
            "read_only": True,
            "source_artifacts": list(GUARDRAIL_SOURCE_ARTIFACTS),
            "forbidden_sources": list(FORBIDDEN_RAW_SOURCES),
            "writes_live_sink": False,
            "semantic_reinterpretation_performed": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "guardrail_checks": checks,
        "readiness": {
            "persisted_artifact_guardrail_ready": True,
            "guardrail_promotes_readiness": False,
            "session_rebuild_ready": False,
            "acontext_sink_ready": False,
            "runtime_parity_proven": False,
            "worker_copyable_doctrine_ready": False,
        },
        "guardrail_verdict": "persisted_artifact_guardrail_passed",
        "next_smallest_proof": [
            "clear Docker, Acontext SDK, local API, and dashboard prerequisites",
            "run one live write/retrieve parity pass with the existing transport packet",
            "keep blocked claims and worker-copyability boundaries visible until live proof passes",
        ],
    }


def write_persisted_artifact_guardrail_fixture(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic proof-block guardrail report."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    report = build_persisted_artifact_guardrail_report(
        proof_anchor_id,
        artifact_dir=base_dir,
    )
    path = base_dir / "persisted_artifact_guardrail.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_guardrail_artifacts(
    artifact_dir: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    return {filename: _load_json(base_dir / filename) for filename in GUARDRAIL_SOURCE_ARTIFACTS}


def _check_blocked_claims_preserved(
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    missing_by_artifact: dict[str, list[str]] = {}
    unsafe_by_artifact: dict[str, list[str]] = {}
    for filename, artifact in artifacts.items():
        boundaries = _required_dict(artifact, "claim_boundaries", filename)
        safe = set(boundaries.get("safe_to_claim", []))
        blocked = set(boundaries.get("do_not_claim_yet", []))
        missing = [claim for claim in REQUIRED_BLOCKED_CLAIMS if claim not in blocked]
        unsafe = [claim for claim in FORBIDDEN_SAFE_CLAIMS if claim in safe]
        if missing:
            missing_by_artifact[filename] = missing
        if unsafe:
            unsafe_by_artifact[filename] = unsafe

    return {
        "check": "blocked_claims_preserved",
        "status": "passed" if not missing_by_artifact and not unsafe_by_artifact else "failed",
        "required_blocked_claims": list(REQUIRED_BLOCKED_CLAIMS),
        "missing_by_artifact": missing_by_artifact,
        "unsafe_safe_claims_by_artifact": unsafe_by_artifact,
    }


def _check_readiness_honesty(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    overclaims: dict[str, dict[str, Any]] = {}
    for filename, artifact in artifacts.items():
        readiness = artifact.get("readiness", {})
        flags = _collect_flag_values(readiness, READINESS_FLAGS_THAT_MUST_REMAIN_FALSE)
        bad = {flag: value for flag, value in flags.items() if value is True}
        if bad:
            overclaims[filename] = bad

    return {
        "check": "readiness_honesty",
        "status": "passed" if not overclaims else "failed",
        "must_remain_false": list(READINESS_FLAGS_THAT_MUST_REMAIN_FALSE),
        "overclaims_by_artifact": overclaims,
    }


def _check_raw_source_independence(
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    violations: dict[str, list[str]] = {}
    for filename, artifact in artifacts.items():
        artifact_violations: list[str] = []
        derived_from = _required_dict(artifact, "derived_from", filename)
        if derived_from.get("read_only") is not True:
            artifact_violations.append("derived_from.read_only must be true")
        if derived_from.get("writes_live_sink") is not False:
            artifact_violations.append("derived_from.writes_live_sink must be false")
        if derived_from.get("semantic_reinterpretation_performed") is not False:
            artifact_violations.append(
                "derived_from.semantic_reinterpretation_performed must be false"
            )
        if derived_from.get("raw_conversation_reopened") is True:
            artifact_violations.append("derived_from.raw_conversation_reopened must be false")
        if derived_from.get("raw_transcript_required") is True:
            artifact_violations.append("derived_from.raw_transcript_required must be false")

        source_artifacts = derived_from.get("source_artifacts", [])
        raw_sources = _find_forbidden_raw_source_strings(source_artifacts)
        if raw_sources:
            artifact_violations.append(
                "derived_from.source_artifacts includes forbidden raw sources: "
                + ", ".join(raw_sources)
            )

        forbidden = set(derived_from.get("forbidden_sources", []))
        missing_forbidden = [
            source for source in REQUIRED_FORBIDDEN_SOURCE_DECLARATIONS if source not in forbidden
        ]
        if missing_forbidden:
            artifact_violations.append(
                "derived_from.forbidden_sources missing: " + ", ".join(missing_forbidden)
            )

        if artifact_violations:
            violations[filename] = artifact_violations

    return {
        "check": "raw_source_independence",
        "status": "passed" if not violations else "failed",
        "forbidden_sources": list(FORBIDDEN_RAW_SOURCES),
        "violations_by_artifact": violations,
    }


def _check_worker_copyability_boundary(
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    drift: dict[str, list[str]] = {}
    for filename, artifact in artifacts.items():
        artifact_drift: list[str] = []
        operator_visibility = artifact.get("operator_visibility")
        if isinstance(operator_visibility, dict):
            if operator_visibility.get("worker_copyable_surface_enabled") is True:
                artifact_drift.append("worker_copyable_surface_enabled became true")
            instruction = operator_visibility.get("copyable_worker_instruction")
            if isinstance(instruction, dict) and instruction.get("allowed") is True:
                artifact_drift.append("copyable_worker_instruction.allowed became true")

        metrics = artifact.get("metrics")
        if isinstance(metrics, dict):
            if metrics.get("worker_copyable_surface_enabled") is True:
                artifact_drift.append("metrics.worker_copyable_surface_enabled became true")
            if metrics.get("copyable_worker_instruction_allowed") is True:
                artifact_drift.append(
                    "metrics.copyable_worker_instruction_allowed became true"
                )

        readiness = artifact.get("readiness")
        if isinstance(readiness, dict) and readiness.get("worker_copyable_doctrine_ready") is True:
            artifact_drift.append("worker_copyable_doctrine_ready became true")

        if artifact_drift:
            drift[filename] = artifact_drift

    return {
        "check": "worker_copyability_boundary",
        "status": "passed" if not drift else "failed",
        "violations_by_artifact": drift,
    }


def _assert_expected_artifacts(artifacts: dict[str, dict[str, Any]]) -> None:
    missing = [filename for filename in GUARDRAIL_SOURCE_ARTIFACTS if filename not in artifacts]
    if missing:
        raise CityOpsContractError(
            "Persisted artifact guardrail missing artifacts: " + ", ".join(missing)
        )


def _assert_no_forbidden_safe_claims(safe_to_claim: list[str]) -> None:
    unsafe = [claim for claim in FORBIDDEN_SAFE_CLAIMS if claim in safe_to_claim]
    if unsafe:
        raise CityOpsContractError(
            "Persisted artifact guardrail cannot mark blocked claims safe: "
            + ", ".join(unsafe)
        )


def _collect_flag_values(value: Any, flags: list[str]) -> dict[str, Any]:
    found: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            if key in flags:
                found[key] = item
            found.update(_collect_flag_values(item, flags))
    elif isinstance(value, list):
        for item in value:
            found.update(_collect_flag_values(item, flags))
    return found


def _find_forbidden_raw_source_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        if value in FORBIDDEN_RAW_SOURCES:
            found.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(_find_forbidden_raw_source_strings(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_find_forbidden_raw_source_strings(item))
    return _dedupe(found)


def _required_dict(artifact: dict[str, Any], key: str, artifact_name: str) -> dict[str, Any]:
    value = artifact.get(key)
    if not isinstance(value, dict):
        raise CityOpsContractError(
            f"Persisted artifact guardrail expected {artifact_name}.{key} to be an object"
        )
    return value


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise CityOpsContractError(f"Expected JSON object at {path}")
    return data


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
