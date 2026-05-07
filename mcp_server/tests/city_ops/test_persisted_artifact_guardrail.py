import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.persisted_artifact_guardrail import (
    PERSISTED_ARTIFACT_GUARDRAIL_SAFE_CLAIM,
    PERSISTED_ARTIFACT_GUARDRAIL_SCHEMA,
    build_persisted_artifact_guardrail_report,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_guardrail_fixture() -> dict:
    with (PROOF_BLOCK_DIR / "persisted_artifact_guardrail.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def load_guardrail_sources() -> dict[str, dict]:
    sources = {}
    for filename in (
        "operator_debug_surface.json",
        "proof_observability_snapshot.json",
        "coordination_intelligence_snapshot.json",
    ):
        with (PROOF_BLOCK_DIR / filename).open("r", encoding="utf-8") as fh:
            sources[filename] = json.load(fh)
    return sources


def test_persisted_artifact_guardrail_report_matches_fixture():
    report = build_persisted_artifact_guardrail_report()

    assert report == read_guardrail_fixture()
    assert report["schema"] == PERSISTED_ARTIFACT_GUARDRAIL_SCHEMA
    assert report["guardrail_verdict"] == "persisted_artifact_guardrail_passed"
    assert PERSISTED_ARTIFACT_GUARDRAIL_SAFE_CLAIM in report["claim_boundaries"][
        "safe_to_claim"
    ]
    assert report["readiness"]["guardrail_promotes_readiness"] is False
    assert report["readiness"]["acontext_sink_ready"] is False


def test_guardrail_fails_when_blocked_claim_is_dropped():
    artifacts = load_guardrail_sources()
    claims = artifacts["coordination_intelligence_snapshot.json"]["claim_boundaries"][
        "do_not_claim_yet"
    ]
    claims.remove("acontext_sink_ready")

    with pytest.raises(CityOpsContractError, match="blocked_claims_preserved"):
        build_persisted_artifact_guardrail_report(artifacts=artifacts)


def test_guardrail_fails_on_readiness_overclaim():
    artifacts = load_guardrail_sources()
    artifacts["proof_observability_snapshot.json"]["readiness"][
        "runtime_parity_proven"
    ] = True

    with pytest.raises(CityOpsContractError, match="readiness_honesty"):
        build_persisted_artifact_guardrail_report(artifacts=artifacts)


def test_guardrail_fails_on_raw_source_dependency():
    artifacts = load_guardrail_sources()
    artifacts["operator_debug_surface.json"]["derived_from"]["source_artifacts"].append(
        "raw_transcript"
    )

    with pytest.raises(CityOpsContractError, match="raw_source_independence"):
        build_persisted_artifact_guardrail_report(artifacts=artifacts)


def test_guardrail_fails_on_worker_copyability_drift():
    artifacts = load_guardrail_sources()
    artifacts["operator_debug_surface.json"]["operator_visibility"][
        "worker_copyable_surface_enabled"
    ] = True
    artifacts["operator_debug_surface.json"]["operator_visibility"][
        "copyable_worker_instruction"
    ]["allowed"] = True

    with pytest.raises(CityOpsContractError, match="worker_copyability_boundary"):
        build_persisted_artifact_guardrail_report(artifacts=artifacts)


def test_guardrail_fails_when_blocked_claim_becomes_safe():
    artifacts = load_guardrail_sources()
    artifacts = copy.deepcopy(artifacts)
    artifacts["proof_observability_snapshot.json"]["claim_boundaries"][
        "safe_to_claim"
    ].append("worker-copyable municipal doctrine")

    with pytest.raises(CityOpsContractError, match="blocked_claims_preserved"):
        build_persisted_artifact_guardrail_report(artifacts=artifacts)
