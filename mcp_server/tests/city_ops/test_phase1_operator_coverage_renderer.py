import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_operator_coverage_renderer import (
    PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME,
    PHASE1_OPERATOR_COVERAGE_RENDERER_SAFE_CLAIM,
    PHASE1_OPERATOR_COVERAGE_RENDERER_SCHEMA,
    build_phase1_operator_coverage_renderer,
    load_phase1_operator_coverage_renderer,
    write_phase1_operator_coverage_renderer,
)
from mcp_server.city_ops.phase1_operator_coverage_summary import (
    PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME,
    build_phase1_operator_coverage_summary,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_operator_coverage_renderer() -> dict:
    with (REVIEWED_FIXTURE_DIR / PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_phase1_operator_coverage_renderer_consumes_summary_only():
    renderer = build_phase1_operator_coverage_renderer()

    assert renderer["schema"] == PHASE1_OPERATOR_COVERAGE_RENDERER_SCHEMA
    assert renderer["derived_from"]["read_only"] is True
    assert renderer["derived_from"]["source_artifacts"] == [
        PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME
    ]
    assert renderer["derived_from"]["consumes_only"] == [
        PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME
    ]
    assert renderer["derived_from"]["reads_raw_review_fixtures"] is False
    assert renderer["derived_from"]["reads_raw_transcripts"] is False
    assert renderer["coverage_totals"] == {
        "reviewed_fixture_count": 3,
        "offer_count": 3,
        "all_phase1_offers_have_reviewed_fixture": True,
    }
    assert PHASE1_OPERATOR_COVERAGE_RENDERER_SAFE_CLAIM in renderer[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_phase1_operator_coverage_renderer_displays_adjacent_claim_boundaries_per_offer():
    renderer = build_phase1_operator_coverage_renderer()

    assert {row["offer_id"] for row in renderer["coverage_table"]} == {
        "counter_reality_check",
        "packet_submission_attempt",
        "posting_compliance_check",
    }
    assert len(renderer["display_lines"]) == 3
    for row, line in zip(renderer["coverage_table"], renderer["display_lines"]):
        assert row["safe_to_claim"]
        assert row["do_not_claim_yet"]
        assert row["readiness_promoted"] is False
        assert "safe=[" in line
        assert "blocked=[" in line
        assert not set(row["safe_to_claim"]) & set(row["do_not_claim_yet"])


def test_phase1_operator_coverage_renderer_matches_persisted_artifact():
    renderer = build_phase1_operator_coverage_renderer()

    assert renderer == read_operator_coverage_renderer()
    assert load_phase1_operator_coverage_renderer() == renderer


def test_phase1_operator_coverage_renderer_blocks_named_overclaims():
    renderer = build_phase1_operator_coverage_renderer()
    blocked = set(renderer["claim_boundaries"]["do_not_claim_yet"])

    assert "customer_copy_ready" in blocked
    assert "operator_ui_ready" in blocked
    assert "dispatch_automation_ready" in blocked
    assert "live_acontext_readiness" in blocked
    assert "erc8004_reputation_ready" in blocked
    assert "worker_skill_dna_ready" in blocked
    assert "legal_sufficiency" in blocked
    assert "regulator_acceptance" in blocked
    assert "exact_gps_or_metadata_exposure" in blocked
    assert "worker_copyable_municipal_doctrine" in blocked
    assert "polished_operator_console_ready" in blocked
    assert "customer_visible_catalog_ready" in blocked
    assert all(value is False for value in renderer["readiness"].values())


def test_phase1_operator_coverage_renderer_refuses_promoted_summary_readiness():
    summary = copy.deepcopy(build_phase1_operator_coverage_summary())
    summary["readiness"]["dispatch_automation_ready"] = True

    with pytest.raises(CityOpsContractError, match="promoted summary readiness"):
        build_phase1_operator_coverage_renderer(summary=summary)


def test_phase1_operator_coverage_renderer_refuses_promoted_offer_row_readiness():
    summary = copy.deepcopy(build_phase1_operator_coverage_summary())
    summary["coverage_by_offer"][0]["promoted_readiness"]["customer_copy_ready"] = True

    with pytest.raises(CityOpsContractError, match="promoted row readiness"):
        build_phase1_operator_coverage_renderer(summary=summary)


def test_phase1_operator_coverage_renderer_refuses_forbidden_safe_claim():
    summary = copy.deepcopy(build_phase1_operator_coverage_summary())
    summary["coverage_by_offer"][0]["claims"]["safe_to_claim"].append(
        "customer_copy_ready"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        build_phase1_operator_coverage_renderer(summary=summary)


def test_write_phase1_operator_coverage_renderer_persists_valid_artifact(tmp_path):
    (tmp_path / PHASE1_OPERATOR_COVERAGE_SUMMARY_FILENAME).write_text(
        json.dumps(build_phase1_operator_coverage_summary()), encoding="utf-8"
    )

    path = write_phase1_operator_coverage_renderer(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME
    assert load_phase1_operator_coverage_renderer(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_load_phase1_operator_coverage_renderer_rejects_readiness_overclaim(tmp_path):
    renderer = build_phase1_operator_coverage_renderer()
    renderer["readiness"]["operator_ui_ready"] = True
    (tmp_path / PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME).write_text(
        json.dumps(renderer), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_phase1_operator_coverage_renderer(fixture_dir=tmp_path)
