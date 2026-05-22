from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_panel import (
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SAFE_CLAIM,
    AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SCHEMA,
    PANEL_ACCESS_FALSE_FLAGS,
    PANEL_BLOCKED_CLAIMS,
    PANEL_FALSE_FLAGS,
    PANEL_READINESS_FALSE_FLAGS,
    build_aas_claim_quarantine_prevented_claim_panel,
    load_aas_claim_quarantine_prevented_claim_panel,
    write_aas_claim_quarantine_prevented_claim_panel,
)
from mcp_server.city_ops.aas_claim_quarantine_read_surface import (
    AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM,
    build_aas_claim_quarantine_read_surface,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_panel() -> dict:
    with (ARTIFACT_DIR / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    for source_path in ARTIFACT_DIR.glob("*.json"):
        (tmp_path / source_path.name).write_text(
            source_path.read_text(encoding="utf-8"), encoding="utf-8"
        )


def test_prevented_claim_panel_matches_persisted_artifact_and_loader():
    panel = build_aas_claim_quarantine_prevented_claim_panel()

    assert panel == read_panel()
    assert load_aas_claim_quarantine_prevented_claim_panel() == panel
    assert panel["schema"] == AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SCHEMA
    assert panel["scope"] == "internal_admin_prevented_claim_panel_only_no_customer_exposure"
    assert panel["panel_status"] == "quarantined_claims_recorded_as_prevented_review_claims"
    assert AAS_CLAIM_QUARANTINE_READ_SURFACE_SAFE_CLAIM in panel["claim_boundaries"]["safe_to_claim"]
    assert AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_SAFE_CLAIM in panel["claim_boundaries"]["safe_to_claim"]


def test_panel_records_every_quarantined_bucket_as_prevented_with_exact_next_proof():
    surface = build_aas_claim_quarantine_read_surface()
    panel = build_aas_claim_quarantine_prevented_claim_panel(surface=surface)

    cards = panel["prevented_claim_cards"]
    assert len(cards) == len(surface["quarantine_bucket_cards"])
    for card, bucket in zip(cards, surface["quarantine_bucket_cards"], strict=True):
        assert card["bucket_id"] == bucket["bucket_id"]
        assert card["review_disposition"] == "prevented_by_claim_quarantine"
        assert card["display_badge"] == "PREVENTED — PROOF REQUIRED"
        assert card["prevented_claims"] == bucket["claims"]
        assert card["prevented_claim_count"] == len(bucket["claims"])
        assert card["exact_next_proof_needed"] == bucket["next_smallest_proof"]
        assert card["operator_action"] == "keep_blocked_until_named_proof_exists"
        assert card["may_override_without_new_proof"] is False
        assert card["may_publish_or_launch"] is False
        assert card["may_dispatch_or_attach_reputation"] is False
        assert card["may_create_worker_copyable_doctrine"] is False


def test_panel_keeps_prevented_claims_out_of_safe_claims_and_inside_blocked_claims():
    surface = build_aas_claim_quarantine_read_surface()
    panel = build_aas_claim_quarantine_prevented_claim_panel(surface=surface)
    prevented_claims = {
        claim
        for bucket in surface["quarantine_bucket_cards"]
        for claim in bucket["claims"]
    }
    boundaries = panel["claim_boundaries"]

    assert not prevented_claims & set(boundaries["safe_to_claim"])
    assert prevented_claims <= set(boundaries["do_not_claim_yet"])
    for claim in PANEL_BLOCKED_CLAIMS:
        assert claim in boundaries["do_not_claim_yet"]
        assert claim not in boundaries["safe_to_claim"]
    assert panel["claim_boundary_footer"]["prevented_claims"] == list(dict.fromkeys(
        claim
        for bucket in surface["quarantine_bucket_cards"]
        for claim in bucket["claims"]
    ))


def test_panel_preserves_internal_admin_only_false_readiness_and_access_flags():
    panel = build_aas_claim_quarantine_prevented_claim_panel()

    assert panel["derived_from"]["read_only"] is True
    assert panel["derived_from"]["semantic_reinterpretation_performed"] is False
    assert panel["access_policy"]["audience"] == "internal_admin_only"
    assert panel["access_policy"]["requires_admin_context"] is True
    for flag in PANEL_FALSE_FLAGS:
        assert panel[flag] is False
    for flag, expected in PANEL_READINESS_FALSE_FLAGS.items():
        assert panel["readiness"][flag] is expected
    for flag in PANEL_ACCESS_FALSE_FLAGS:
        assert panel["access_policy"][flag] is False
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
        assert panel["derived_from"][flag] is False


def test_next_proof_queue_is_interpreted_as_proof_needed_not_authority():
    panel = build_aas_claim_quarantine_prevented_claim_panel()

    assert panel["next_proof_queue"]
    for item in panel["next_proof_queue"]:
        assert item["panel_interpretation"] == (
            "proof_needed_before_any_matching_claim_can_leave_prevented_state"
        )
        assert item["customer_or_dispatch_authority_created_by_queue_item"] is False


def test_write_panel_persists_valid_artifact(tmp_path):
    seed_sources(tmp_path)

    path = write_aas_claim_quarantine_prevented_claim_panel(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_CLAIM_QUARANTINE_PREVENTED_CLAIM_PANEL_FILENAME
    assert load_aas_claim_quarantine_prevented_claim_panel(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_launch_promotion_fails_closed():
    surface = copy.deepcopy(build_aas_claim_quarantine_read_surface())
    surface["quarantine_bucket_cards"][0]["may_publish_or_launch"] = True

    with pytest.raises(CityOpsContractError, match="source bucket launch promoted"):
        build_aas_claim_quarantine_prevented_claim_panel(surface=surface)


def test_source_missing_next_proof_fails_closed():
    surface = copy.deepcopy(build_aas_claim_quarantine_read_surface())
    surface["quarantine_bucket_cards"][0]["next_smallest_proof"] = ""

    with pytest.raises(CityOpsContractError, match="source bucket missing next proof"):
        build_aas_claim_quarantine_prevented_claim_panel(surface=surface)


def test_panel_forbidden_safe_claim_fails_closed():
    surface = build_aas_claim_quarantine_read_surface()
    panel = build_aas_claim_quarantine_prevented_claim_panel(surface=surface)
    panel = copy.deepcopy(panel)
    panel["claim_boundaries"]["safe_to_claim"].append("customer_delivery_approved")

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_panel import (
            _assert_panel_is_conservative,
        )

        _assert_panel_is_conservative(panel, surface)


def test_panel_card_launch_promotion_fails_closed():
    surface = build_aas_claim_quarantine_read_surface()
    panel = build_aas_claim_quarantine_prevented_claim_panel(surface=surface)
    panel = copy.deepcopy(panel)
    panel["prevented_claim_cards"][0]["may_publish_or_launch"] = True

    with pytest.raises(CityOpsContractError, match="prevented-claim card promoted"):
        from mcp_server.city_ops.aas_claim_quarantine_prevented_claim_panel import (
            _assert_panel_is_conservative,
        )

        _assert_panel_is_conservative(panel, surface)
