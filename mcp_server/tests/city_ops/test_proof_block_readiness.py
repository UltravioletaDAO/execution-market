import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.proof_block_readiness import (
    PROOF_BLOCK_READINESS_SAFE_CLAIM,
    PROOF_BLOCK_READINESS_SCHEMA,
    READINESS_SOURCE_ARTIFACTS,
    build_proof_block_readiness_summary,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_readiness_fixture() -> dict:
    with (PROOF_BLOCK_DIR / "proof_block_readiness_summary.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def load_readiness_sources() -> dict[str, dict]:
    sources = {}
    for filename in READINESS_SOURCE_ARTIFACTS:
        with (PROOF_BLOCK_DIR / filename).open("r", encoding="utf-8") as fh:
            sources[filename] = json.load(fh)
    return sources


def make_attemptable_sources() -> dict[str, dict]:
    artifacts = load_readiness_sources()
    preflight = artifacts["acontext_live_preflight_result.json"]
    preflight["readiness"].update(
        {
            "docker_available": True,
            "acontext_python_sdk_available": True,
            "local_acontext_api_reachable": True,
            "local_acontext_dashboard_reachable": True,
            "ready_to_attempt_live_transport": True,
            "blockers": [],
        }
    )
    preflight["probe"]["docker"].update({"available": True, "exit_code": 0, "error": None})
    preflight["probe"]["python_sdk"]["available"] = True
    preflight["probe"]["api"].update({"reachable": True, "status_code": 200, "error": None})
    preflight["probe"]["dashboard"].update(
        {"reachable": True, "status_code": 200, "error": None}
    )
    preflight["preflight_verdict"] = "live_transport_can_be_attempted_without_readiness_claim"
    return artifacts


def test_proof_block_readiness_summary_matches_fixture():
    summary = build_proof_block_readiness_summary()

    assert summary == read_readiness_fixture()
    assert summary["schema"] == PROOF_BLOCK_READINESS_SCHEMA
    assert summary["readiness_summary_verdict"] == (
        "persisted_artifacts_ready_but_live_prerequisites_blocked"
    )
    assert PROOF_BLOCK_READINESS_SAFE_CLAIM in summary["claim_boundaries"][
        "safe_to_claim"
    ]
    assert summary["readiness"]["persisted_artifacts_sufficient_for_live_attempt"] is True
    assert summary["readiness"]["operational_prerequisites_satisfied"] is False
    assert summary["readiness"]["ready_to_attempt_live_transport"] is False
    assert summary["readiness"]["acontext_sink_ready"] is False
    assert summary["readiness"]["missing_prerequisites"] == [
        "docker_daemon_unavailable",
        "acontext_python_sdk_missing",
        "local_acontext_api_unreachable",
        "local_acontext_dashboard_unreachable",
    ]


def test_readiness_summary_can_be_attemptable_without_promoting_sink_readiness():
    summary = build_proof_block_readiness_summary(artifacts=make_attemptable_sources())

    assert summary["readiness_summary_verdict"] == "persisted_artifacts_ready_for_live_attempt"
    assert summary["readiness"]["ready_to_attempt_live_transport"] is True
    assert summary["readiness"]["operational_prerequisites_satisfied"] is True
    assert summary["readiness"]["acontext_sink_ready"] is False
    assert summary["readiness"]["runtime_parity_proven"] is False
    assert summary["readiness"]["session_rebuild_ready"] is False
    assert "acontext_live_transport_parity_landed" in summary["claim_boundaries"][
        "do_not_claim_yet"
    ]


def test_readiness_summary_fails_when_safe_claim_drifts():
    artifacts = load_readiness_sources()
    artifacts["persisted_artifact_guardrail.json"]["claim_boundaries"][
        "safe_to_claim"
    ].append("runtime_parity_proven")

    with pytest.raises(CityOpsContractError, match="claim_boundary_drift"):
        build_proof_block_readiness_summary(artifacts=artifacts)


def test_readiness_summary_fails_when_blocked_claim_is_dropped():
    artifacts = load_readiness_sources()
    artifacts["operator_debug_surface.json"]["claim_boundaries"][
        "do_not_claim_yet"
    ].remove("acontext_sink_ready")

    with pytest.raises(CityOpsContractError, match="claim_boundary_drift"):
        build_proof_block_readiness_summary(artifacts=artifacts)


def test_readiness_summary_fails_on_readiness_overclaim():
    artifacts = load_readiness_sources()
    artifacts["coordination_intelligence_snapshot.json"]["readiness"][
        "runtime_parity_proven"
    ] = True

    with pytest.raises(CityOpsContractError, match="readiness_honesty"):
        build_proof_block_readiness_summary(artifacts=artifacts)


def test_readiness_summary_fails_on_raw_source_dependency():
    artifacts = load_readiness_sources()
    artifacts["proof_observability_snapshot.json"]["derived_from"][
        "source_artifacts"
    ].append("raw_transcript")

    with pytest.raises(CityOpsContractError, match="raw_source_independence"):
        build_proof_block_readiness_summary(artifacts=artifacts)


def test_readiness_summary_fails_on_worker_copyability_drift():
    artifacts = load_readiness_sources()
    artifacts["operator_debug_surface.json"]["operator_visibility"][
        "copyable_worker_instruction"
    ]["allowed"] = True

    with pytest.raises(CityOpsContractError, match="worker_copyability_boundary"):
        build_proof_block_readiness_summary(artifacts=artifacts)


def test_readiness_summary_fails_when_doctrine_is_implied_while_copyability_false():
    artifacts = load_readiness_sources()
    artifacts = copy.deepcopy(artifacts)
    artifacts["persisted_artifact_guardrail.json"]["readiness"][
        "worker_copyable_doctrine_ready"
    ] = True

    with pytest.raises(CityOpsContractError, match="readiness_honesty"):
        build_proof_block_readiness_summary(artifacts=artifacts)


def test_readiness_summary_fails_when_required_artifact_is_missing():
    artifacts = load_readiness_sources()
    artifacts.pop("acontext_live_preflight_result.json")

    with pytest.raises(CityOpsContractError, match="missing artifacts"):
        build_proof_block_readiness_summary(artifacts=artifacts)
