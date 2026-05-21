import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_claim_quarantine_board import (
    AAS_CLAIM_QUARANTINE_BOARD_FILENAME,
    AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM,
    build_aas_claim_quarantine_board,
)
from mcp_server.city_ops.aas_claim_quarantine_read_surface import (
    AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME,
    AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_READ_SURFACE_SCHEMA,
    ACCESS_FALSE_FLAGS,
    READ_SURFACE_BLOCKED_CLAIMS,
    READINESS_FALSE_FLAGS,
    SURFACE_FALSE_FLAGS,
    build_aas_claim_quarantine_read_surface,
    load_aas_claim_quarantine_read_surface,
    write_aas_claim_quarantine_read_surface,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_surface() -> dict:
    with (ARTIFACT_DIR / AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    for source_path in ARTIFACT_DIR.glob("*.json"):
        (tmp_path / source_path.name).write_text(
            source_path.read_text(encoding="utf-8"), encoding="utf-8"
        )


def test_surface_matches_persisted_artifact_and_loader():
    surface = build_aas_claim_quarantine_read_surface()

    assert surface == read_surface()
    assert load_aas_claim_quarantine_read_surface() == surface
    assert surface["schema"] == AAS_CLAIM_QUARANTINE_READ_SURFACE_SCHEMA
    assert surface["scope"] == "internal_admin_claim_quarantine_read_surface_only_no_customer_exposure"
    assert surface["surface_status"] == "read_only_launch_claim_quarantine_surface_landed_not_route"
    assert AAS_CLAIM_QUARANTINE_BOARD_SAFE_CLAIM in surface["claim_boundaries"]["safe_to_claim"]
    assert AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM in surface["claim_boundaries"]["safe_to_claim"]


def test_surface_is_read_only_internal_admin_and_registers_no_route():
    surface = build_aas_claim_quarantine_read_surface()

    assert surface["derived_from"]["read_only"] is True
    assert surface["derived_from"]["semantic_reinterpretation_performed"] is False
    assert surface["access_policy"]["audience"] == "internal_admin_only"
    assert surface["access_policy"]["requires_admin_context"] is True
    for flag in ACCESS_FALSE_FLAGS:
        assert surface["access_policy"][flag] is False
    assert surface["render_contract"]["network_route_registered"] is False
    assert surface["render_contract"]["public_route_registered"] is False


def test_surface_preserves_all_false_readiness_and_authority_flags():
    surface = build_aas_claim_quarantine_read_surface()

    for flag in SURFACE_FALSE_FLAGS:
        assert surface[flag] is False
    for flag in READINESS_FALSE_FLAGS:
        assert surface["readiness"][flag] is False
    for flag in [
        "writes_live_acontext",
        "retrieves_live_acontext",
        "writes_customer_copy",
        "enables_dispatch_automation",
        "emits_reputation_receipts",
        "reverifies_payment_coverage",
        "reverifies_production_infrastructure",
        "exposes_gps_or_metadata",
        "publishes_worker_doctrine",
    ]:
        assert surface["derived_from"][flag] is False


def test_bucket_cards_are_sticky_quarantine_cards():
    surface = build_aas_claim_quarantine_read_surface()

    cards = surface["quarantine_bucket_cards"]
    assert [card["bucket_id"] for card in cards] == [
        "customer_and_public_exposure",
        "pricing_and_operator_launch",
        "dispatch_reputation_and_worker_dna",
        "runtime_payment_and_production",
        "location_metadata_and_domain_authority",
    ]
    for card in cards:
        assert card["status"] == "quarantined_not_safe_to_claim"
        assert card["display_badge"] == "QUARANTINED — NOT SAFE TO CLAIM"
        assert card["safe_to_use_now"] == "internal_admin_review_and_planning_only"
        assert card["may_publish_or_launch"] is False
        assert card["claim_count"] == len(card["claims"])
        assert card["next_smallest_proof"]


def test_claim_footer_keeps_safe_and_blocked_claims_separate():
    surface = build_aas_claim_quarantine_read_surface()
    boundaries = surface["claim_boundaries"]
    footer = surface["claim_boundary_footer"]

    assert footer["safe_to_claim"] == boundaries["safe_to_claim"]
    assert footer["do_not_claim_yet"] == boundaries["do_not_claim_yet"]
    assert footer["safe_claim_count"] == len(boundaries["safe_to_claim"])
    assert footer["blocked_claim_count"] == len(boundaries["do_not_claim_yet"])
    assert not set(boundaries["safe_to_claim"]) & set(boundaries["do_not_claim_yet"])
    for claim in READ_SURFACE_BLOCKED_CLAIMS:
        assert claim in boundaries["do_not_claim_yet"]
        assert claim not in boundaries["safe_to_claim"]


def test_source_summary_does_not_promote_launch_counts():
    surface = build_aas_claim_quarantine_read_surface()
    summary = surface["source_summary"]

    assert summary["family_count"] == 3
    assert summary["human_approval_records"] == 1
    assert summary["delivery_authorizations"] == 0
    assert summary["publishable_families"] == 0
    assert summary["dispatch_ready_families"] == 0
    assert summary["runtime_parity_families"] == 0
    assert summary["gps_release_ready_families"] == 0
    assert summary["honest_claim_scope"] == "internal_admin_read_surface_only"


def test_write_surface_persists_valid_artifact(tmp_path):
    seed_sources(tmp_path)

    path = write_aas_claim_quarantine_read_surface(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME
    assert load_aas_claim_quarantine_read_surface(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_bucket_launch_promotion_fails_closed():
    board = copy.deepcopy(build_aas_claim_quarantine_board())
    board["quarantine_buckets"][0]["may_publish_or_launch"] = True

    with pytest.raises(CityOpsContractError, match="source bucket launch promoted"):
        build_aas_claim_quarantine_read_surface(board=board)


def test_surface_public_route_flip_fails_closed(tmp_path):
    seed_sources(tmp_path)
    surface = build_aas_claim_quarantine_read_surface(artifact_dir=tmp_path)
    surface["render_contract"]["public_route_registered"] = True
    (tmp_path / AAS_CLAIM_QUARANTINE_READ_SURFACE_FILENAME).write_text(
        json.dumps(surface), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="registered public_route_registered"):
        load_aas_claim_quarantine_read_surface(artifact_dir=tmp_path)


def test_surface_forbidden_safe_claim_fails_closed():
    surface = build_aas_claim_quarantine_read_surface()
    surface = copy.deepcopy(surface)
    surface["claim_boundaries"]["safe_to_claim"].append("customer_delivery_approved")

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        board = build_aas_claim_quarantine_board()
        from mcp_server.city_ops.aas_claim_quarantine_read_surface import _assert_surface_conservative

        _assert_surface_conservative(surface, board)
