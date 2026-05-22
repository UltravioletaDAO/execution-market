from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_trend_read_surface import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SCHEMA,
    TREND_READ_SURFACE_BLOCKED_CLAIMS,
    build_aas_claim_quarantine_prevented_claim_trend_read_surface,
    load_aas_claim_quarantine_prevented_claim_trend_read_surface,
    write_aas_claim_quarantine_prevented_claim_trend_read_surface,
)
from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_trend_summary import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME,
    build_aas_claim_quarantine_prevented_claim_trend_summary,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_surface() -> dict:
    with (
        ARTIFACT_DIR / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    for source_path in ARTIFACT_DIR.glob("*.json"):
        if source_path.name == AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME:
            continue
        (tmp_path / source_path.name).write_text(
            source_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def test_trend_read_surface_matches_persisted_artifact_and_loader():
    surface = build_aas_claim_quarantine_prevented_claim_trend_read_surface()

    assert surface == read_surface()
    assert load_aas_claim_quarantine_prevented_claim_trend_read_surface() == surface
    assert surface["schema"] == AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SCHEMA
    assert surface["scope"] == "internal_admin_prevented_claim_trend_cards_only_no_route"
    assert surface["surface_verdict"] == "prevented_claim_trend_cards_ready_for_internal_review_only"
    assert surface["source_artifact"]["file"] == AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_SUMMARY_FILENAME
    assert AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_SAFE_CLAIM in surface[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_operator_cards_preserve_top_trends_and_next_proofs():
    surface = build_aas_claim_quarantine_prevented_claim_trend_read_surface()
    summary = build_aas_claim_quarantine_prevented_claim_trend_summary()

    assert len(surface["operator_cards"]) == len(summary["trend_rows"]) == 5
    assert surface["operator_cards"][0]["prevented_claim_count"] >= surface["operator_cards"][-1][
        "prevented_claim_count"
    ]
    assert all(card["exact_next_proof_needed"] for card in surface["operator_cards"])
    assert all(card["may_publish_or_launch"] is False for card in surface["operator_cards"])
    assert all(
        card["may_leave_quarantine_without_named_proof"] is False
        for card in surface["operator_cards"]
    )


def test_connection_map_answers_late_night_pattern_questions_without_promoting_runtime():
    surface = build_aas_claim_quarantine_prevented_claim_trend_read_surface()
    connections = {item["connection"]: item for item in surface["connection_map"]}

    assert set(connections) == {
        "memory_patterns_to_reviewed_proof_slots",
        "irc_coordination_to_state_cards",
        "cross_project_intelligence_to_priority_firewall",
        "agent_success_metrics_to_restraint_reputation_candidate",
        "claim_quarantine_to_product_surface_sequence",
    }
    assert connections["memory_patterns_to_reviewed_proof_slots"]["authorizes_live_acontext"] is False
    assert connections["irc_coordination_to_state_cards"]["authorizes_runtime_mutation"] is False
    assert connections["cross_project_intelligence_to_priority_firewall"]["authorizes_autorouting"] is False
    assert connections["agent_success_metrics_to_restraint_reputation_candidate"][
        "emits_reputation_receipts"
    ] is False
    assert connections["claim_quarantine_to_product_surface_sequence"][
        "authorizes_customer_or_public_surface"
    ] is False


def test_trend_read_surface_keeps_all_launch_claims_blocked():
    surface = build_aas_claim_quarantine_prevented_claim_trend_read_surface()

    safe = set(surface["claim_boundaries"]["safe_to_claim"])
    blocked = set(surface["claim_boundaries"]["do_not_claim_yet"])
    assert safe.isdisjoint(blocked)
    assert set(TREND_READ_SURFACE_BLOCKED_CLAIMS) <= blocked
    for claim in [
        "trend_read_surface_authorizes_customer_delivery",
        "trend_read_surface_authorizes_dispatch",
        "trend_read_surface_authorizes_erc8004_reputation",
        "trend_read_surface_creates_worker_copyable_aas_doctrine",
    ]:
        assert claim in blocked
        assert claim not in safe


def test_trend_read_surface_preserves_false_readiness_and_access_flags():
    surface = build_aas_claim_quarantine_prevented_claim_trend_read_surface()

    assert surface["derived_from"]["read_only"] is True
    assert surface["derived_from"]["adds_route"] is False
    assert surface["access_policy"]["audience"] == "internal_admin_only"
    assert surface["access_policy"]["network_route_registered"] is False
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
        assert surface["readiness"][flag] is False


def test_write_trend_read_surface_persists_from_sources(tmp_path):
    seed_sources(tmp_path)

    path = write_aas_claim_quarantine_prevented_claim_trend_read_surface(
        artifact_dir=tmp_path
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_TREND_READ_SURFACE_FILENAME
    assert persisted["readiness"]["operator_cards_ready"] is True
    assert persisted["claim_boundary_footer"]["operator_card_count"] == 5


def test_trend_read_surface_refuses_source_proof_bypass():
    summary = copy.deepcopy(build_aas_claim_quarantine_prevented_claim_trend_summary())
    summary["trend_summary"]["claims_can_leave_prevented_state_without_named_proof"] = True

    with pytest.raises(CityOpsContractError, match="proof bypass"):
        build_aas_claim_quarantine_prevented_claim_trend_read_surface(
            trend_summary=summary
        )


def test_trend_read_surface_refuses_source_access_promotion():
    summary = copy.deepcopy(build_aas_claim_quarantine_prevented_claim_trend_summary())
    summary["access_policy"]["customer_visible"] = True

    with pytest.raises(CityOpsContractError, match="customer_visible"):
        build_aas_claim_quarantine_prevented_claim_trend_read_surface(
            trend_summary=summary
        )


def test_trend_read_surface_refuses_card_promotion():
    surface = build_aas_claim_quarantine_prevented_claim_trend_read_surface()
    summary = build_aas_claim_quarantine_prevented_claim_trend_summary()
    surface["operator_cards"][0]["may_dispatch_or_attach_reputation"] = True

    from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_trend_read_surface import (  # noqa: PLC0415
        _assert_trend_read_surface_contract,
    )

    with pytest.raises(CityOpsContractError, match="may_dispatch_or_attach_reputation"):
        _assert_trend_read_surface_contract(surface, summary)


def test_trend_read_surface_refuses_readiness_promotion():
    surface = build_aas_claim_quarantine_prevented_claim_trend_read_surface()
    summary = build_aas_claim_quarantine_prevented_claim_trend_summary()
    surface["readiness"]["public_or_catalog_route_ready"] = True

    from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_trend_read_surface import (  # noqa: PLC0415
        _assert_trend_read_surface_contract,
    )

    with pytest.raises(CityOpsContractError, match="public_or_catalog_route_ready"):
        _assert_trend_read_surface_contract(surface, summary)
