import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_operator_coverage_read_surface import (
    PHASE1_OPERATOR_COVERAGE_READ_SURFACE_FILENAME,
    PHASE1_OPERATOR_COVERAGE_READ_SURFACE_SAFE_CLAIM,
    PHASE1_OPERATOR_COVERAGE_READ_SURFACE_SCHEMA,
    build_phase1_operator_coverage_read_surface,
    load_phase1_operator_coverage_read_surface,
    write_phase1_operator_coverage_read_surface,
)
from mcp_server.city_ops.phase1_operator_coverage_renderer import (
    PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME,
    build_phase1_operator_coverage_renderer,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_operator_coverage_read_surface() -> dict:
    with (REVIEWED_FIXTURE_DIR / PHASE1_OPERATOR_COVERAGE_READ_SURFACE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_phase1_operator_coverage_read_surface_consumes_renderer_only():
    surface = build_phase1_operator_coverage_read_surface()

    assert surface["schema"] == PHASE1_OPERATOR_COVERAGE_READ_SURFACE_SCHEMA
    assert surface["derived_from"]["read_only"] is True
    assert surface["derived_from"]["source_artifacts"] == [
        PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME
    ]
    assert surface["derived_from"]["consumes_only"] == [
        PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME
    ]
    assert surface["access_policy"]["audience"] == "internal_admin_only"
    assert surface["access_policy"]["requires_admin_context"] is True
    assert surface["access_policy"]["public_route_registered"] is False
    assert surface["mount_contract"]["network_route_registered"] is False
    assert surface["mount_contract"]["method"] == "GET"
    assert PHASE1_OPERATOR_COVERAGE_READ_SURFACE_SAFE_CLAIM in surface[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_phase1_operator_coverage_read_surface_preserves_renderer_payload_as_is():
    renderer = build_phase1_operator_coverage_renderer()
    surface = build_phase1_operator_coverage_read_surface(renderer=renderer)

    assert surface["coverage_totals"] == renderer["coverage_totals"]
    assert surface["coverage_table"] == renderer["coverage_table"]
    assert surface["display_lines"] == renderer["display_lines"]
    assert {row["offer_id"] for row in surface["coverage_table"]} == {
        "counter_reality_check",
        "packet_submission_attempt",
        "posting_compliance_check",
    }
    for row in surface["coverage_table"]:
        assert row["safe_to_claim"]
        assert row["do_not_claim_yet"]
        assert row["readiness_promoted"] is False
        assert not set(row["safe_to_claim"]) & set(row["do_not_claim_yet"])


def test_phase1_operator_coverage_read_surface_matches_persisted_artifact():
    surface = build_phase1_operator_coverage_read_surface()

    assert surface == read_operator_coverage_read_surface()
    assert load_phase1_operator_coverage_read_surface() == surface


def test_phase1_operator_coverage_read_surface_blocks_external_or_product_claims():
    surface = build_phase1_operator_coverage_read_surface()
    blocked = set(surface["claim_boundaries"]["do_not_claim_yet"])

    assert "public_route_ready" in blocked
    assert "customer_visible_catalog_ready" in blocked
    assert "customer_copy_ready" in blocked
    assert "polished_operator_console_ready" in blocked
    assert "operator_ui_ready" in blocked
    assert "worker_instruction_surface_ready" in blocked
    assert "dispatch_routing_ready" in blocked
    assert "dispatch_automation_ready" in blocked
    assert "live_acontext_readiness" in blocked
    assert "acontext_sink_ready" in blocked
    assert "erc8004_reputation_ready" in blocked
    assert "worker_skill_dna_ready" in blocked
    assert "legal_sufficiency" in blocked
    assert "regulator_acceptance" in blocked
    assert "exact_gps_or_metadata_exposure" in blocked
    assert "worker_copyable_municipal_doctrine" in blocked
    assert all(value is False for value in surface["readiness"].values())


def test_phase1_operator_coverage_read_surface_cards_keep_safe_and_blocked_visible():
    surface = build_phase1_operator_coverage_read_surface()
    cards = {card["card"]: card for card in surface["read_surface_cards"]}

    assert cards["coverage_totals"]["status"] == "visible_internal_admin_only"
    assert cards["safe_to_claim"]["status"] == "visible_without_softening"
    assert PHASE1_OPERATOR_COVERAGE_READ_SURFACE_SAFE_CLAIM in cards[
        "safe_to_claim"
    ]["values"]
    assert cards["do_not_claim_yet"]["status"] == "visible_without_softening"
    assert "customer_copy_ready" in cards["do_not_claim_yet"]["values"]
    assert cards["phase1_offer_rows"]["status"] == "renderer_payload_pass_through"


def test_phase1_operator_coverage_read_surface_refuses_promoted_renderer_readiness():
    renderer = copy.deepcopy(build_phase1_operator_coverage_renderer())
    renderer["readiness"]["dispatch_automation_ready"] = True

    with pytest.raises(CityOpsContractError, match="promoted renderer readiness"):
        build_phase1_operator_coverage_read_surface(renderer=renderer)


def test_load_phase1_operator_coverage_read_surface_rejects_public_access_upgrade(tmp_path):
    surface = build_phase1_operator_coverage_read_surface()
    surface["access_policy"]["public_route_registered"] = True
    (tmp_path / PHASE1_OPERATOR_COVERAGE_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="access overclaims"):
        load_phase1_operator_coverage_read_surface(fixture_dir=tmp_path)


def test_write_phase1_operator_coverage_read_surface_persists_valid_artifact(tmp_path):
    (tmp_path / PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME).write_text(
        json.dumps(build_phase1_operator_coverage_renderer()), encoding="utf-8"
    )

    path = write_phase1_operator_coverage_read_surface(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_OPERATOR_COVERAGE_READ_SURFACE_FILENAME
    assert load_phase1_operator_coverage_read_surface(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )
