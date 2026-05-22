from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_panel import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
    build_aas_claim_quarantine_prevented_claim_panel,
)
from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_trend_summary import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SCHEMA,
    TREND_SUMMARY_BLOCKED_CLAIMS,
    build_aas_claim_quarantine_prevented_claim_trend_summary,
    load_aas_claim_quarantine_prevented_claim_trend_summary,
    write_aas_claim_quarantine_prevented_claim_trend_summary,
)
from mcp_server.city_ops.aas_claim_quarantine_route_panel_handoff_packet import (
    AAS_CLAIM_QUARANTINE_ROUTE_PANEL_HANDOFF_PACKET_FILENAME,
    build_aas_claim_quarantine_route_panel_handoff_packet,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_summary() -> dict:
    with (
        ARTIFACT_DIR / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    for source_path in ARTIFACT_DIR.glob("*.json"):
        if source_path.name == AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME:
            continue
        (tmp_path / source_path.name).write_text(
            source_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def test_prevented_claim_trend_summary_matches_persisted_artifact_and_loader():
    summary = build_aas_claim_quarantine_prevented_claim_trend_summary()

    assert summary == read_summary()
    assert load_aas_claim_quarantine_prevented_claim_trend_summary() == summary
    assert summary["schema"] == AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SCHEMA
    assert summary["scope"] == "internal_admin_prevented_claim_trend_summary_only_no_customer_exposure"
    assert summary["summary_verdict"] == "prevented_claim_trend_summary_ready_for_internal_review_learning_only"
    assert AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_SAFE_CLAIM in summary[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_trend_rows_rank_prevented_buckets_and_keep_next_proofs():
    summary = build_aas_claim_quarantine_prevented_claim_trend_summary()
    rows = summary["trend_rows"]

    assert len(rows) == 5
    assert summary["trend_summary"]["source_bucket_count"] == 5
    assert summary["trend_summary"]["prevented_claim_count"] == 30
    assert rows[0]["prevented_claim_count"] >= rows[-1]["prevented_claim_count"]
    assert summary["trend_summary"]["top_prevented_bucket"] == rows[0]["bucket_id"]
    assert all(row["exact_next_proof_needed"] for row in rows)
    assert all(row["review_disposition"] == "prevented_by_claim_quarantine" for row in rows)


def test_trend_summary_keeps_prevented_claims_blocked():
    panel = build_aas_claim_quarantine_prevented_claim_panel()
    summary = build_aas_claim_quarantine_prevented_claim_trend_summary(
        prevented_claim_panel=panel
    )
    prevented = set(panel["claim_boundary_footer"]["prevented_claims"])
    boundaries = summary["claim_boundaries"]

    assert prevented
    assert not prevented & set(boundaries["safe_to_claim"])
    assert prevented <= set(boundaries["do_not_claim_yet"])
    for claim in TREND_SUMMARY_BLOCKED_CLAIMS:
        assert claim in boundaries["do_not_claim_yet"]
        assert claim not in boundaries["safe_to_claim"]


def test_summary_preserves_false_readiness_and_access_flags():
    summary = build_aas_claim_quarantine_prevented_claim_trend_summary()

    assert summary["derived_from"]["read_only"] is True
    assert summary["derived_from"]["adds_route"] is False
    assert summary["derived_from"]["semantic_reinterpretation_performed"] is False
    assert summary["access_policy"]["audience"] == "internal_admin_only"
    assert summary["access_policy"]["requires_admin_context"] is True
    for flag in [
        "public_route_registered",
        "catalog_route_registered",
        "customer_visible",
        "worker_visible",
        "dispatch_enabled",
        "writes_live_acontext",
        "retrieves_live_acontext",
        "emits_reputation_receipts",
        "exposes_gps_or_metadata",
        "publishes_worker_doctrine",
    ]:
        assert summary["access_policy"][flag] is False
    for flag in [
        "customer_copy_ready",
        "customer_delivery_ready",
        "publication_ready",
        "public_or_catalog_route_ready",
        "dispatch_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "live_acontext_runtime_parity_ready",
        "payment_or_production_reverified",
        "exact_gps_or_raw_metadata_release_ready",
        "domain_authority_ready",
        "worker_copyable_doctrine_ready",
    ]:
        assert summary["readiness"][flag] is False


def test_integration_signals_connect_system_integration_focus_without_live_mutation():
    summary = build_aas_claim_quarantine_prevented_claim_trend_summary()
    signals = {item["signal"]: item for item in summary["integration_signals"]}

    assert signals["memory_to_acontext_candidate"]["writes_live_acontext"] is False
    assert signals["irc_session_management"]["changes_irc_runtime"] is False
    assert signals["cross_project_decision_support"]["cross_project_autorouting_enabled"] is False
    assert signals["agent_observability_success_metrics"]["emits_reputation_receipts"] is False
    assert "30 prevented claims" in signals["agent_observability_success_metrics"]["evidence"]


def test_write_summary_persists_from_sources(tmp_path):
    seed_sources(tmp_path)

    path = write_aas_claim_quarantine_prevented_claim_trend_summary(artifact_dir=tmp_path)
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME
    assert persisted["readiness"]["source_handoff_verified"] is True
    assert persisted["readiness"]["source_panel_verified"] is True
    assert persisted["trend_summary"]["prevented_claim_count"] == 30


def test_trend_summary_refuses_handoff_public_access_promotion():
    packet = copy.deepcopy(build_aas_claim_quarantine_route_panel_handoff_packet())
    packet["access_policy"]["customer_visible"] = True

    with pytest.raises(CityOpsContractError, match="customer_visible"):
        build_aas_claim_quarantine_prevented_claim_trend_summary(handoff_packet=packet)


def test_trend_summary_refuses_panel_proof_bypass():
    panel = copy.deepcopy(build_aas_claim_quarantine_prevented_claim_panel())
    panel["prevented_claim_summary"][
        "claims_can_leave_prevented_state_without_named_proof"
    ] = True

    with pytest.raises(CityOpsContractError, match="proof-bypass"):
        build_aas_claim_quarantine_prevented_claim_trend_summary(prevented_claim_panel=panel)


def test_trend_summary_refuses_prevented_claim_promotion():
    panel = copy.deepcopy(build_aas_claim_quarantine_prevented_claim_panel())
    claim = panel["claim_boundary_footer"]["prevented_claims"][0]
    panel["claim_boundaries"]["safe_to_claim"].append(claim)

    with pytest.raises(CityOpsContractError, match="claim overlap"):
        build_aas_claim_quarantine_prevented_claim_trend_summary(prevented_claim_panel=panel)


def test_trend_summary_refuses_promoted_row():
    summary = build_aas_claim_quarantine_prevented_claim_trend_summary()
    packet = build_aas_claim_quarantine_route_panel_handoff_packet()
    panel = build_aas_claim_quarantine_prevented_claim_panel()
    summary["trend_rows"][0]["may_dispatch_or_attach_reputation"] = True

    from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_trend_summary import (  # noqa: PLC0415
        _assert_trend_summary_contract,
    )

    with pytest.raises(CityOpsContractError, match="may_dispatch_or_attach_reputation"):
        _assert_trend_summary_contract(summary, packet, panel)
