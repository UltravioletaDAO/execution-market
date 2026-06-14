"""Tests for the internal/admin Visible Asset State Snapshot state menu."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_concept_gap_implementation_roadmap import (
    write_aas_concept_gap_implementation_roadmap,
)
from mcp_server.city_ops.aas_concept_gap_matrix import write_aas_concept_gap_matrix
from mcp_server.city_ops.aas_field_asset_visible_state_fixture_outline import (
    AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_FILENAME,
    AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM,
    FIELD_ASSET_VISIBLE_STATE_BLOCKED_CLAIMS,
    build_aas_field_asset_visible_state_fixture_outline,
    write_aas_field_asset_visible_state_fixture_outline,
)
from mcp_server.city_ops.aas_visible_asset_state_internal_state_menu import (
    AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_FILENAME,
    AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SAFE_CLAIM,
    AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SCHEMA,
    AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_STATUS,
    FALSE_FLAGS,
    REQUIRED_STATE_CODES,
    STATE_MENU_ROWS,
    VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_BLOCKED_CLAIMS,
    build_aas_visible_asset_state_internal_state_menu,
    load_aas_visible_asset_state_internal_state_menu,
    write_aas_visible_asset_state_internal_state_menu,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_state_menu() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_visible_asset_state_menu_matches_persisted_artifact_and_loader() -> None:
    menu = build_aas_visible_asset_state_internal_state_menu()

    assert menu == read_state_menu()
    assert load_aas_visible_asset_state_internal_state_menu() == menu
    assert menu["schema"] == AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SCHEMA
    assert menu["state_menu_status"] == AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_STATUS
    assert AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM in menu[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_SAFE_CLAIM in menu[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_visible_asset_state_menu_consumes_field_asset_outline_by_digest() -> None:
    menu = build_aas_visible_asset_state_internal_state_menu()
    source = menu["source_outline"]

    assert source["file"] == AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_FILENAME
    assert source["safe_claim"] == AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM
    assert source["consumed_family"] == "field_asset_ops"
    assert source["canonical_family"] == "Visible Asset State Snapshot"
    assert len(source["digest_sha256"]) == 64


def test_visible_asset_state_menu_is_held_internal_admin_state_menu_only() -> None:
    menu = build_aas_visible_asset_state_internal_state_menu()

    for key, expected in FALSE_FLAGS.items():
        assert menu["readiness"][key] is expected
    assert menu["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "asset_class_selected": False,
        "collection_method_authorized": False,
        "selected_decision": None,
        "recommended_no_human_posture": "state_menu_only",
    }

    body = menu["visible_asset_state_internal_state_menu"]
    assert body["canonical_family"] == "Visible Asset State Snapshot"
    assert body["legacy_source_family"] == "field_asset_ops"
    assert body["allowed_use"] == (
        "internal_admin_state_menu_only_no_asset_class_no_field_visit_no_customer_copy"
    )
    assert body["menu_mode"] == "state_menu_only"
    assert body["still_blocked"] is True
    assert body["next_gate_before_any_delivery_or_runtime_movement"] == (
        "separate_asset_class_method_boundary_and_operator_answer_receipt"
    )


def test_visible_asset_state_menu_rows_preserve_required_codes_and_truth_families() -> None:
    menu = build_aas_visible_asset_state_internal_state_menu()
    body = menu["visible_asset_state_internal_state_menu"]
    rows = body["state_menu_rows"]

    assert rows == STATE_MENU_ROWS
    assert [row["state_code"] for row in rows] == REQUIRED_STATE_CODES
    assert body["required_state_codes"] == REQUIRED_STATE_CODES
    assert set(body["allowed_truth_families"]) == {
        "operator_truth",
        "collection_truth",
        "location_privacy_truth",
        "authority_truth",
    }
    for row in rows:
        assert row["allowed_observation_values"]
        assert row["safe_internal_read"]
        assert row["forbidden_promotion"].startswith("does_not_")
        assert row["missing_truth_family"] in body["allowed_truth_families"]


def test_visible_asset_state_menu_preserves_claim_boundaries_and_firewall() -> None:
    menu = build_aas_visible_asset_state_internal_state_menu()
    safe = set(menu["claim_boundaries"]["safe_to_claim"])
    blocked = set(menu["claim_boundaries"]["do_not_claim_yet"])

    assert set(FIELD_ASSET_VISIBLE_STATE_BLOCKED_CLAIMS) <= blocked
    assert set(VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_answer_receipt",
        "selects_asset_class_future_answer_or_collection_method",
        "authorizes_field_visit_access_recipient_or_customer_use",
        "authorizes_inspection_repair_remediation_or_maintenance",
        "certifies_functionality_safety_warranty_or_sla",
        "releases_exact_gps_raw_metadata_private_context_or_pii",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert menu["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_visible_asset_state_menu_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)
    write_aas_field_asset_visible_state_fixture_outline(artifact_dir=tmp_path)
    path = write_aas_visible_asset_state_internal_state_menu(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_FILENAME
    assert load_aas_visible_asset_state_internal_state_menu(artifact_dir=tmp_path)[
        "state_menu_id"
    ] == "execution_market.aas.visible_asset_state_internal_state_menu.2026_06_14_0100"


def test_visible_asset_state_menu_rejects_promoted_source_outline() -> None:
    outline = copy.deepcopy(build_aas_field_asset_visible_state_fixture_outline())
    outline["readiness"]["outline_authorizes_inspection_repair_or_remediation"] = True

    with pytest.raises(CityOpsContractError, match="source readiness promoted"):
        build_aas_visible_asset_state_internal_state_menu(source_outline=outline)


def test_visible_asset_state_menu_rejects_asset_class_selection() -> None:
    menu = build_aas_visible_asset_state_internal_state_menu()
    menu["current_operator_state"]["asset_class_selected"] = True

    with pytest.raises(CityOpsContractError, match="asset_class_selected"):
        load_aas_visible_asset_state_internal_state_menu(artifact_dir=_write_fixture_quad(menu))


def test_visible_asset_state_menu_rejects_missing_required_state_code() -> None:
    menu = build_aas_visible_asset_state_internal_state_menu()
    rows = menu["visible_asset_state_internal_state_menu"]["state_menu_rows"]
    menu["visible_asset_state_internal_state_menu"]["state_menu_rows"] = [
        row for row in rows if row["state_code"] != "visible_indicator_state"
    ]

    with pytest.raises(CityOpsContractError, match="state code drift"):
        load_aas_visible_asset_state_internal_state_menu(artifact_dir=_write_fixture_quad(menu))


def test_visible_asset_state_menu_rejects_customer_dispatch_or_privacy_promotion() -> None:
    menu = build_aas_visible_asset_state_internal_state_menu()
    menu["readiness"]["menu_creates_catalog_pricing_quote_route_queue_or_dispatch"] = True

    with pytest.raises(CityOpsContractError, match="catalog_pricing_quote_route_queue_or_dispatch"):
        load_aas_visible_asset_state_internal_state_menu(artifact_dir=_write_fixture_quad(menu))

    menu = build_aas_visible_asset_state_internal_state_menu()
    menu["readiness"]["menu_releases_exact_gps_raw_metadata_private_context_or_pii"] = True

    with pytest.raises(CityOpsContractError, match="raw_metadata_private_context_or_pii"):
        load_aas_visible_asset_state_internal_state_menu(artifact_dir=_write_fixture_quad(menu))


def _write_fixture_quad(menu: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp)
    write_aas_field_asset_visible_state_fixture_outline(artifact_dir=tmp)
    (tmp / AAS_VISIBLE_ASSET_STATE_INTERNAL_STATE_MENU_FILENAME).write_text(
        json.dumps(menu, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tmp
