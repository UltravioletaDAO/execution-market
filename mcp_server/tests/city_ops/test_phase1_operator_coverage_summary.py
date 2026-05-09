import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_operator_coverage_summary import (
    PHASE1_OPERATOR_COVERAGE_ARTIFACT_SAFE_CLAIM,
    PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME,
    PHASE1_OPERATOR_COVERAGE_SUMMARY_SAFE_CLAIM,
    PHASE1_OPERATOR_COVERAGE_SUMMARY_SCHEMA,
    build_phase1_operator_coverage_summary,
    load_phase1_operator_coverage_summary,
    write_phase1_operator_coverage_summary,
)
from mcp_server.city_ops.phase1_reviewed_fixtures import (
    PHASE1_REVIEWED_FIXTURE_REGISTRY_FILENAME,
    PHASE1_REVIEWED_FIXTURE_REGISTRY_SAFE_CLAIM,
    build_phase1_reviewed_fixture_registry_summary,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_operator_coverage_summary() -> dict:
    with (REVIEWED_FIXTURE_DIR / PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_phase1_operator_coverage_summary_counts_reviewed_registry_only():
    summary = build_phase1_operator_coverage_summary()

    assert summary["schema"] == PHASE1_OPERATOR_COVERAGE_SUMMARY_SCHEMA
    assert summary["derived_from"]["read_only"] is True
    assert summary["derived_from"]["source_artifact"] == (
        "phase1_reviewed_fixture_registry_summary.json"
    )
    assert summary["coverage_totals"] == {
        "reviewed_fixture_count": 3,
        "offer_count": 3,
        "all_phase1_offers_have_reviewed_fixture": True,
    }
    assert {row["offer_id"] for row in summary["coverage_by_offer"]} == {
        "counter_reality_check",
        "packet_submission_attempt",
        "posting_compliance_check",
    }
    assert PHASE1_REVIEWED_FIXTURE_REGISTRY_SAFE_CLAIM in summary["claim_boundaries"][
        "safe_to_claim"
    ]
    assert PHASE1_OPERATOR_COVERAGE_SUMMARY_SAFE_CLAIM in summary["claim_boundaries"][
        "safe_to_claim"
    ]
    assert PHASE1_OPERATOR_COVERAGE_ARTIFACT_SAFE_CLAIM in summary["claim_boundaries"][
        "safe_to_claim"
    ]


def test_phase1_operator_coverage_summary_matches_persisted_artifact():
    summary = build_phase1_operator_coverage_summary()

    assert summary == read_operator_coverage_summary()
    assert load_phase1_operator_coverage_summary() == summary


def test_phase1_operator_coverage_summary_preserves_adjacent_claims_per_offer():
    summary = build_phase1_operator_coverage_summary()

    assert not (
        set(summary["claim_boundaries"]["safe_to_claim"])
        & set(summary["claim_boundaries"]["do_not_claim_yet"])
    )
    for row in summary["coverage_by_offer"]:
        assert row["claims"]["safe_to_claim"]
        assert row["claims"]["do_not_claim_yet"]
        assert not (
            set(row["claims"]["safe_to_claim"])
            & set(row["claims"]["do_not_claim_yet"])
        )
        assert row["promoted_readiness"] == {
            "customer_copy_ready": False,
            "dispatch_automation_ready": False,
            "live_acontext_ready": False,
            "legal_or_regulator_ready": False,
            "gps_or_metadata_exposure_allowed": False,
            "worker_copyable_municipal_doctrine_ready": False,
        }


def test_phase1_operator_coverage_summary_blocks_named_overclaims_explicitly():
    summary = build_phase1_operator_coverage_summary()
    blocked = set(summary["claim_boundaries"]["do_not_claim_yet"])

    assert "customer_copy_ready" in blocked
    assert "dispatch_automation_ready" in blocked
    assert "live_acontext_readiness" in blocked
    assert "acontext_sink_ready" in blocked
    assert "erc8004_reputation_ready" in blocked
    assert "worker_skill_dna_ready" in blocked
    assert "legal_sufficiency" in blocked
    assert "regulator_acceptance" in blocked
    assert "exact_gps_or_metadata_exposure" in blocked
    assert "worker_copyable_municipal_doctrine" in blocked
    assert all(value is False for value in summary["readiness"].values())


def test_phase1_operator_coverage_summary_refuses_forbidden_safe_claim():
    registry = build_phase1_reviewed_fixture_registry_summary()
    registry["safe_to_claim"].append("customer_copy_ready")

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        build_phase1_operator_coverage_summary(registry=registry)


def test_phase1_operator_coverage_summary_refuses_commercial_scope_upgrade():
    registry = build_phase1_reviewed_fixture_registry_summary()
    registry["commercial_scope"]["autonomous_dispatch_enabled"] = True

    with pytest.raises(CityOpsContractError, match="commercial scope overclaim"):
        build_phase1_operator_coverage_summary(registry=registry)


def test_phase1_operator_coverage_summary_refuses_dropped_adjacent_claims():
    registry = copy.deepcopy(build_phase1_reviewed_fixture_registry_summary())
    registry["coverage_by_offer"]["packet_submission_attempt"]["do_not_claim_yet"] = []

    with pytest.raises(CityOpsContractError, match="missing do_not_claim_yet"):
        build_phase1_operator_coverage_summary(registry=registry)


def test_phase1_operator_coverage_summary_refuses_gps_metadata_exposure():
    registry = build_phase1_reviewed_fixture_registry_summary()
    registry["operator_observability"]["exact_gps_or_metadata_exposed"] = True

    with pytest.raises(CityOpsContractError, match="GPS or metadata"):
        build_phase1_operator_coverage_summary(registry=registry)


def test_write_phase1_operator_coverage_summary_persists_valid_artifact(tmp_path):
    (tmp_path / PHASE1_REVIEWED_FIXTURE_REGISTRY_FILENAME).write_text(
        json.dumps(build_phase1_reviewed_fixture_registry_summary()), encoding="utf-8"
    )

    path = write_phase1_operator_coverage_summary(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME
    assert load_phase1_operator_coverage_summary(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_load_phase1_operator_coverage_summary_rejects_readiness_overclaim(tmp_path):
    summary = build_phase1_operator_coverage_summary()
    summary["readiness"]["dispatch_automation_ready"] = True
    (tmp_path / PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME).write_text(
        json.dumps(summary), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_phase1_operator_coverage_summary(fixture_dir=tmp_path)
