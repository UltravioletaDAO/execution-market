"""Read-only readiness summary for CaaS proof-block live transport.

This module answers one narrow question over persisted proof-block artifacts:
are the artifacts and local prerequisites sufficient to attempt a live Acontext
write/retrieve parity run?  It never calls Acontext, never writes a sink, and
never upgrades truth semantics.  Its job is to keep the current blocked state
inspectable while failing loudly on claim drift, raw-source dependency,
readiness overclaim, or worker-copyability promotion.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import CityOpsContractError
from .proof_block_artifacts import DEFAULT_PROOF_ANCHOR_ID, _default_proof_block_dir

PROOF_BLOCK_READINESS_SCHEMA = "city_ops.proof_block_readiness_summary.v1"
PROOF_BLOCK_READINESS_SAFE_CLAIM = "proof_block_readiness_summary_landed"

READINESS_SOURCE_ARTIFACTS = [
    "session_rebuild_report.json",
    "acontext_transport_parity_result.json",
    "acontext_live_preflight_result.json",
    "operator_debug_surface.json",
    "proof_observability_snapshot.json",
    "coordination_intelligence_snapshot.json",
    "persisted_artifact_guardrail.json",
]

EXPECTED_SAFE_CLAIMS_BY_ARTIFACT = {
    "session_rebuild_report.json": [
        "projection_truth_landed",
        "reuse_parity_landed",
        "session_rebuild_consumer_landed",
        "session_rebuild_report_fixture_landed",
    ],
    "acontext_transport_parity_result.json": [
        "projection_truth_landed",
        "reuse_parity_landed",
        "session_rebuild_consumer_landed",
        "session_rebuild_report_fixture_landed",
        "acontext_transport_parity_test_landed",
    ],
    "acontext_live_preflight_result.json": [
        "projection_truth_landed",
        "reuse_parity_landed",
        "session_rebuild_consumer_landed",
        "session_rebuild_report_fixture_landed",
        "acontext_transport_parity_test_landed",
        "acontext_live_preflight_landed",
    ],
    "operator_debug_surface.json": [
        "projection_truth_landed",
        "reuse_parity_landed",
        "session_rebuild_consumer_landed",
        "session_rebuild_report_fixture_landed",
        "acontext_transport_parity_test_landed",
        "acontext_live_preflight_landed",
        "thin_operator_debug_surface_landed",
    ],
    "proof_observability_snapshot.json": [
        "projection_truth_landed",
        "reuse_parity_landed",
        "session_rebuild_consumer_landed",
        "session_rebuild_report_fixture_landed",
        "acontext_transport_parity_test_landed",
        "acontext_live_preflight_landed",
        "thin_operator_debug_surface_landed",
        "proof_observability_metrics_landed",
    ],
    "coordination_intelligence_snapshot.json": [
        "projection_truth_landed",
        "reuse_parity_landed",
        "session_rebuild_consumer_landed",
        "session_rebuild_report_fixture_landed",
        "acontext_transport_parity_test_landed",
        "acontext_live_preflight_landed",
        "thin_operator_debug_surface_landed",
        "proof_observability_metrics_landed",
        "coordination_intelligence_snapshot_landed",
    ],
    "persisted_artifact_guardrail.json": [
        "projection_truth_landed",
        "reuse_parity_landed",
        "session_rebuild_consumer_landed",
        "session_rebuild_report_fixture_landed",
        "acontext_transport_parity_test_landed",
        "acontext_live_preflight_landed",
        "thin_operator_debug_surface_landed",
        "proof_observability_metrics_landed",
        "coordination_intelligence_snapshot_landed",
        "persisted_artifact_guardrail_landed",
    ],
}

BASE_BLOCKED_CLAIMS = [
    "runtime_parity_proven",
    "reuse_behavior_proven",
    "closure_proof_ready",
    "closure_proof_landed",
    "session_rebuild_ready",
    "acontext_sink_ready",
    "worker-copyable municipal doctrine",
]
LIVE_BLOCKED_CLAIMS = [
    "acontext_live_write_completed",
    "acontext_live_retrieval_completed",
    "acontext_live_transport_parity_landed",
]
SURFACE_BLOCKED_CLAIMS = [
    "polished_review_console_ready",
    "office_memory_view_ready",
    "broad_operator_workflow_ready",
]
COORDINATION_BLOCKED_CLAIMS = [
    "multi_jurisdiction_playbook_ready",
    "autonomous_city_dispatch_ready",
]

EXPECTED_BLOCKED_CLAIMS_BY_ARTIFACT = {
    "session_rebuild_report.json": BASE_BLOCKED_CLAIMS,
    "acontext_transport_parity_result.json": BASE_BLOCKED_CLAIMS,
    "acontext_live_preflight_result.json": [*BASE_BLOCKED_CLAIMS, *LIVE_BLOCKED_CLAIMS],
    "operator_debug_surface.json": [
        *BASE_BLOCKED_CLAIMS,
        *LIVE_BLOCKED_CLAIMS,
        *SURFACE_BLOCKED_CLAIMS,
    ],
    "proof_observability_snapshot.json": [
        *BASE_BLOCKED_CLAIMS,
        *LIVE_BLOCKED_CLAIMS,
        *SURFACE_BLOCKED_CLAIMS,
    ],
    "coordination_intelligence_snapshot.json": [
        *BASE_BLOCKED_CLAIMS,
        *LIVE_BLOCKED_CLAIMS,
        *SURFACE_BLOCKED_CLAIMS,
        *COORDINATION_BLOCKED_CLAIMS,
    ],
    "persisted_artifact_guardrail.json": [
        *BASE_BLOCKED_CLAIMS,
        *LIVE_BLOCKED_CLAIMS,
        *SURFACE_BLOCKED_CLAIMS,
        *COORDINATION_BLOCKED_CLAIMS,
    ],
}

FORBIDDEN_SAFE_CLAIMS = [
    "closure_proof_ready",
    "closure_proof_landed",
    "session_rebuild_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "acontext_live_write_completed",
    "acontext_live_retrieval_completed",
    "acontext_live_transport_parity_landed",
    "worker-copyable municipal doctrine",
    "worker-copyable doctrine",
    "worker_copyable_doctrine_ready",
]
READINESS_FLAGS_THAT_MUST_NOT_BE_TRUE = [
    "session_rebuild_ready",
    "acontext_sink_ready",
    "runtime_parity_proven",
    "live_acontext_write_performed",
    "live_acontext_retrieval_performed",
    "worker_copyable_doctrine_ready",
]
LIVE_ATTEMPT_PREREQUISITES = {
    "docker_available": "docker_daemon_unavailable",
    "acontext_python_sdk_available": "acontext_python_sdk_missing",
    "local_acontext_api_reachable": "local_acontext_api_unreachable",
    "local_acontext_dashboard_reachable": "local_acontext_dashboard_unreachable",
}
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


def build_proof_block_readiness_summary(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
    artifacts: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a conservative readiness summary from persisted proof artifacts.

    The summary may report that the persisted artifact chain is internally ready
    for a live parity attempt, but the live attempt itself remains blocked unless
    the preflight fixture says Docker, SDK, API, and dashboard prerequisites are
    present.  Any truth drift raises ``CityOpsContractError`` before a summary is
    emitted.
    """

    source_artifacts = artifacts or _load_readiness_artifacts(artifact_dir)
    _assert_expected_artifacts(source_artifacts)
    _assert_identity_preserved(proof_anchor_id, source_artifacts)

    checks = [
        _check_claim_boundary_drift(source_artifacts),
        _check_readiness_honesty(source_artifacts),
        _check_raw_source_independence(source_artifacts),
        _check_worker_copyability_boundary(source_artifacts),
        _check_live_attempt_prerequisites(source_artifacts),
    ]
    hard_failures = [
        check
        for check in checks
        if check["status"] == "failed"
        or (check["check"] != "live_attempt_prerequisites" and check["status"] != "passed")
    ]
    if hard_failures:
        raise CityOpsContractError(
            "Proof-block readiness summary failed: "
            + "; ".join(f"{check['check']}={check['status']}" for check in hard_failures)
        )

    preflight = source_artifacts["acontext_live_preflight_result.json"]
    guardrail = source_artifacts["persisted_artifact_guardrail.json"]
    identity = _identity_from(source_artifacts["session_rebuild_report.json"])
    missing_prerequisites = checks[-1]["missing_prerequisites"]
    persisted_artifacts_sufficient = all(
        check["status"] == "passed" for check in checks if check["check"] != "live_attempt_prerequisites"
    )
    operational_prerequisites_satisfied = not missing_prerequisites
    ready_to_attempt = persisted_artifacts_sufficient and operational_prerequisites_satisfied

    inherited_safe = list(guardrail["claim_boundaries"].get("safe_to_claim", []))
    safe_to_claim = _dedupe([*inherited_safe, PROOF_BLOCK_READINESS_SAFE_CLAIM])
    do_not_claim_yet = _dedupe(
        [
            *guardrail["claim_boundaries"].get("do_not_claim_yet", []),
            *LIVE_BLOCKED_CLAIMS,
            "acontext_sink_ready",
            "runtime_parity_proven",
            "session_rebuild_ready",
            "worker-copyable municipal doctrine",
        ]
    )
    _assert_no_forbidden_safe_claims(safe_to_claim)

    return {
        "schema": PROOF_BLOCK_READINESS_SCHEMA,
        "summary_id": f"proof_block_readiness:{proof_anchor_id}",
        "proof_anchor_id": proof_anchor_id,
        "coordination_session_id": identity["coordination_session_id"],
        "compact_decision_id": identity["compact_decision_id"],
        "review_packet_id": identity["review_packet_id"],
        "derived_from": {
            "read_only": True,
            "source_artifacts": list(READINESS_SOURCE_ARTIFACTS),
            "forbidden_sources": list(FORBIDDEN_RAW_SOURCES),
            "writes_live_sink": False,
            "semantic_reinterpretation_performed": False,
            "raw_conversation_reopened": False,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "inherited_safe_to_claim": inherited_safe,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "readiness": {
            "proof_block_readiness_summary_ready": True,
            "summary_promotes_readiness": False,
            "persisted_artifacts_sufficient_for_live_attempt": persisted_artifacts_sufficient,
            "operational_prerequisites_satisfied": operational_prerequisites_satisfied,
            "ready_to_attempt_live_transport": ready_to_attempt,
            "acontext_sink_ready": False,
            "session_rebuild_ready": False,
            "runtime_parity_proven": False,
            "worker_copyable_doctrine_ready": False,
            "live_acontext_write_performed": False,
            "live_acontext_retrieval_performed": False,
            "missing_prerequisites": list(missing_prerequisites),
            "preflight_blockers": list(preflight["readiness"].get("blockers", [])),
        },
        "summary_checks": checks,
        "readiness_summary_verdict": (
            "persisted_artifacts_ready_for_live_attempt"
            if ready_to_attempt
            else "persisted_artifacts_ready_but_live_prerequisites_blocked"
        ),
        "next_smallest_proof": _next_smallest_proof(missing_prerequisites),
    }


def write_proof_block_readiness_summary_fixture(
    proof_anchor_id: str = DEFAULT_PROOF_ANCHOR_ID,
    *,
    artifact_dir: str | Path | None = None,
) -> Path:
    """Persist the deterministic proof-block readiness summary fixture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    summary = build_proof_block_readiness_summary(
        proof_anchor_id,
        artifact_dir=base_dir,
    )
    path = base_dir / "proof_block_readiness_summary.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_readiness_artifacts(
    artifact_dir: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    return {filename: _load_json(base_dir / filename) for filename in READINESS_SOURCE_ARTIFACTS}


def _check_claim_boundary_drift(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    drift: dict[str, dict[str, Any]] = {}
    unsafe_by_artifact: dict[str, list[str]] = {}
    for filename, artifact in artifacts.items():
        boundaries = _required_dict(artifact, "claim_boundaries", filename)
        actual_safe = list(boundaries.get("safe_to_claim") or [])
        actual_blocked = list(boundaries.get("do_not_claim_yet") or [])
        expected_safe = EXPECTED_SAFE_CLAIMS_BY_ARTIFACT[filename]
        expected_blocked = EXPECTED_BLOCKED_CLAIMS_BY_ARTIFACT[filename]
        if actual_safe != expected_safe or actual_blocked != expected_blocked:
            drift[filename] = {
                "expected_safe_to_claim": expected_safe,
                "actual_safe_to_claim": actual_safe,
                "expected_do_not_claim_yet": expected_blocked,
                "actual_do_not_claim_yet": actual_blocked,
            }
        unsafe = [claim for claim in FORBIDDEN_SAFE_CLAIMS if claim in actual_safe]
        if unsafe:
            unsafe_by_artifact[filename] = unsafe

    return {
        "check": "claim_boundary_drift",
        "status": "passed" if not drift and not unsafe_by_artifact else "failed",
        "safe_to_claim_drift_by_artifact": drift,
        "unsafe_safe_claims_by_artifact": unsafe_by_artifact,
    }


def _check_readiness_honesty(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    overclaims: dict[str, dict[str, Any]] = {}
    for filename, artifact in artifacts.items():
        values = _collect_flag_values(artifact.get("readiness", {}), READINESS_FLAGS_THAT_MUST_NOT_BE_TRUE)
        bad = {flag: value for flag, value in values.items() if value is True}
        if bad:
            overclaims[filename] = bad

    return {
        "check": "readiness_honesty",
        "status": "passed" if not overclaims else "failed",
        "must_not_be_true": list(READINESS_FLAGS_THAT_MUST_NOT_BE_TRUE),
        "overclaims_by_artifact": overclaims,
    }


def _check_raw_source_independence(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    violations: dict[str, list[str]] = {}
    for filename, artifact in artifacts.items():
        artifact_violations: list[str] = []
        for source_key in ("derived_from", "source_read_contract", "transport_contract"):
            value = artifact.get(source_key)
            if not isinstance(value, dict):
                continue
            _append_source_contract_violations(
                artifact_violations,
                source_key,
                value,
                require_read_only=(source_key != "transport_contract"),
            )
        if artifact_violations:
            violations[filename] = artifact_violations

    return {
        "check": "raw_source_independence",
        "status": "passed" if not violations else "failed",
        "forbidden_sources": list(FORBIDDEN_RAW_SOURCES),
        "violations_by_artifact": violations,
    }


def _check_worker_copyability_boundary(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    drift: dict[str, list[str]] = {}
    for filename, artifact in artifacts.items():
        artifact_drift: list[str] = []
        _collect_worker_copyability_drift(artifact, artifact_drift)
        if artifact_drift:
            drift[filename] = _dedupe(artifact_drift)

    return {
        "check": "worker_copyability_boundary",
        "status": "passed" if not drift else "failed",
        "violations_by_artifact": drift,
    }


def _check_live_attempt_prerequisites(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    preflight = artifacts["acontext_live_preflight_result.json"]
    readiness = _required_dict(preflight, "readiness", "acontext_live_preflight_result.json")
    missing = [
        missing_label
        for flag, missing_label in LIVE_ATTEMPT_PREREQUISITES.items()
        if readiness.get(flag) is not True
    ]
    fixture_ready = bool(readiness.get("ready_to_attempt_live_transport"))
    if fixture_ready and missing:
        status = "failed"
    elif missing:
        status = "blocked"
    else:
        status = "passed"

    return {
        "check": "live_attempt_prerequisites",
        "status": status,
        "required_prerequisites": list(LIVE_ATTEMPT_PREREQUISITES),
        "missing_prerequisites": missing,
        "preflight_ready_to_attempt_live_transport": fixture_ready,
    }


def _append_source_contract_violations(
    violations: list[str],
    source_key: str,
    contract: dict[str, Any],
    *,
    require_read_only: bool,
) -> None:
    if require_read_only and "read_only" in contract and contract.get("read_only") is not True:
        violations.append(f"{source_key}.read_only must be true")
    if "writes_live_sink" in contract and contract.get("writes_live_sink") is not False:
        violations.append(f"{source_key}.writes_live_sink must be false")
    if (
        "semantic_reinterpretation_performed" in contract
        and contract.get("semantic_reinterpretation_performed") is not False
    ):
        violations.append(f"{source_key}.semantic_reinterpretation_performed must be false")
    if contract.get("raw_transcript_required") is True:
        violations.append(f"{source_key}.raw_transcript_required must be false")
    if contract.get("raw_conversation_reopened") is True:
        violations.append(f"{source_key}.raw_conversation_reopened must be false")

    source_artifacts = contract.get("source_artifacts", [])
    raw_sources = _find_forbidden_raw_source_strings(source_artifacts)
    if raw_sources:
        violations.append(
            f"{source_key}.source_artifacts includes forbidden raw sources: "
            + ", ".join(raw_sources)
        )

    forbidden_sources = contract.get("forbidden_sources")
    if isinstance(forbidden_sources, list):
        missing_forbidden = [
            source for source in REQUIRED_FORBIDDEN_SOURCE_DECLARATIONS if source not in forbidden_sources
        ]
        if missing_forbidden:
            violations.append(
                f"{source_key}.forbidden_sources missing: " + ", ".join(missing_forbidden)
            )


def _collect_worker_copyability_drift(value: Any, drift: list[str], path: str = "") -> None:
    if isinstance(value, dict):
        if value.get("worker_copyable_surface_enabled") is True:
            drift.append(f"{path}.worker_copyable_surface_enabled became true".lstrip("."))
        if value.get("copyable_worker_instruction_allowed") is True:
            drift.append(f"{path}.copyable_worker_instruction_allowed became true".lstrip("."))
        if value.get("worker_copyable_doctrine_ready") is True:
            drift.append(f"{path}.worker_copyable_doctrine_ready became true".lstrip("."))
        if value.get("allowed") is True and "copyable_worker_instruction" in path:
            drift.append(f"{path}.allowed became true")
        for key, item in value.items():
            _collect_worker_copyability_drift(item, drift, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _collect_worker_copyability_drift(item, drift, f"{path}[{index}]")


def _assert_expected_artifacts(artifacts: dict[str, dict[str, Any]]) -> None:
    missing = [filename for filename in READINESS_SOURCE_ARTIFACTS if filename not in artifacts]
    if missing:
        raise CityOpsContractError(
            "Proof-block readiness summary missing artifacts: " + ", ".join(missing)
        )


def _assert_identity_preserved(
    proof_anchor_id: str,
    artifacts: dict[str, dict[str, Any]],
) -> None:
    identities = {filename: _identity_from(artifact) for filename, artifact in artifacts.items()}
    expected = identities["session_rebuild_report.json"]
    if expected["proof_anchor_id"] != proof_anchor_id:
        raise CityOpsContractError(
            f"Proof-block readiness summary expected proof anchor {proof_anchor_id!r}"
        )
    drift = {filename: identity for filename, identity in identities.items() if identity != expected}
    if drift:
        raise CityOpsContractError("Proof-block readiness summary identity drifted")


def _identity_from(artifact: dict[str, Any]) -> dict[str, str]:
    identity = artifact.get("identity")
    if isinstance(identity, dict):
        return {
            "proof_anchor_id": _required_str(identity, "proof_anchor_id"),
            "coordination_session_id": _required_str(identity, "coordination_session_id"),
            "compact_decision_id": _required_str(identity, "compact_decision_id"),
            "review_packet_id": _required_str(identity, "review_packet_id"),
        }
    return {
        "proof_anchor_id": _required_str(artifact, "proof_anchor_id"),
        "coordination_session_id": _required_str(artifact, "coordination_session_id"),
        "compact_decision_id": _required_str(artifact, "compact_decision_id"),
        "review_packet_id": _required_str(artifact, "review_packet_id"),
    }


def _assert_no_forbidden_safe_claims(safe_to_claim: list[str]) -> None:
    unsafe = [claim for claim in FORBIDDEN_SAFE_CLAIMS if claim in safe_to_claim]
    if unsafe:
        raise CityOpsContractError(
            "Proof-block readiness summary cannot mark blocked claims safe: "
            + ", ".join(unsafe)
        )


def _next_smallest_proof(missing_prerequisites: list[str]) -> list[str]:
    if missing_prerequisites:
        return [
            "clear missing local Acontext prerequisites: " + ", ".join(missing_prerequisites),
            "rerun the live preflight fixture until ready_to_attempt_live_transport=true",
            "then run exactly one live write/retrieve pass using the existing transport packet",
            "reuse assert_acontext_transport_parity before claiming any live transport label",
        ]
    return [
        "run exactly one live local Acontext write/retrieve pass using the existing packet",
        "retrieve by proof_anchor_id, packet_id, and namespace",
        "reuse assert_acontext_transport_parity before claiming acontext_live_transport_parity_landed",
        "keep acontext_sink_ready=false until live retrieval proves no semantic strengthening",
    ]


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
        raise CityOpsContractError(f"Proof-block readiness summary expected {artifact_name}.{key}")
    return value


def _required_str(artifact: dict[str, Any], key: str) -> str:
    value = artifact.get(key)
    if not isinstance(value, str) or not value:
        raise CityOpsContractError(f"Proof-block readiness summary expected string {key}")
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
