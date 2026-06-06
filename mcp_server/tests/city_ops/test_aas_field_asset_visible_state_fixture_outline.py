"""Tests for the internal/admin AAS Field Asset Ops visible-state fixture outline."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_concept_gap_implementation_roadmap import (
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    build_aas_concept_gap_implementation_roadmap,
    write_aas_concept_gap_implementation_roadmap,
)
from mcp_server.city_ops.aas_concept_gap_matrix import write_aas_concept_gap_matrix
from mcp_server.city_ops.aas_field_asset_visible_state_fixture_outline import (
    AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_FILENAME,
    AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM,
    AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SCHEMA,
    AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_STATUS,
    FALSE_FLAGS,
    FIELD_ASSET_VISIBLE_STATE_BLOCKED_CLAIMS,
    FORBIDDEN_LANGUAGE,
    OBSERVATION_BOUNDARIES,
    VISIBLE_STATE_FIELDS,
    build_aas_field_asset_visible_state_fixture_outline,
    load_aas_field_asset_visible_state_fixture_outline,
    write_aas_field_asset_visible_state_fixture_outline,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture_outline() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_field_asset_outline_matches_persisted_artifact_and_loader() -> None:
    outline = build_aas_field_asset_visible_state_fixture_outline()

    assert outline == read_fixture_outline()
    assert load_aas_field_asset_visible_state_fixture_outline() == outline
    assert outline["schema"] == AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SCHEMA
    assert outline["fixture_outline_status"] == AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_STATUS
    assert AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM in outline["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_SAFE_CLAIM in outline[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_field_asset_outline_consumes_rank_four_roadmap_row_by_digest() -> None:
    outline = build_aas_field_asset_visible_state_fixture_outline()
    source = outline["source_roadmap"]

    assert source["file"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME
    assert source["safe_claim"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM
    assert source["consumed_row_family"] == "field_asset_ops"
    assert source["consumed_row_rank"] == 4
    assert len(source["digest_sha256"]) == 64


def test_field_asset_outline_is_concept_only_not_repair_sla_or_dispatch() -> None:
    outline = build_aas_field_asset_visible_state_fixture_outline()

    for key, expected in FALSE_FLAGS.items():
        assert outline["readiness"][key] is expected
    assert outline["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_decision": None,
        "recommended_no_human_posture": "concept_outline_only",
    }

    fixture = outline["field_asset_visible_state_fixture_outline"]
    assert fixture["aas_family"] == "field_asset_ops"
    assert fixture["allowed_use"] == (
        "internal_admin_visible_asset_state_fixture_outline_no_repair_or_sla_language"
    )
    assert fixture["concept_mode"] == "concept_outline_only"
    assert fixture["still_blocked"] is True
    assert fixture["next_gate_before_any_delivery_or_runtime_movement"] == (
        "separate_explicit_operator_answer_receipt_then_field_asset_ops_customer_or_dispatch_gate"
    )


def test_field_asset_outline_preserves_visible_state_and_language_boundaries() -> None:
    outline = build_aas_field_asset_visible_state_fixture_outline()
    fixture = outline["field_asset_visible_state_fixture_outline"]

    assert set(VISIBLE_STATE_FIELDS) <= set(fixture["visible_state_fields"])
    assert set(OBSERVATION_BOUNDARIES) <= set(fixture["observation_boundaries"])
    assert set(FORBIDDEN_LANGUAGE) <= set(fixture["forbidden_language"])
    assert "visible asset state outline only" in fixture["safe_internal_language"]
    assert "repair and SLA language blocked" in fixture["safe_internal_language"]
    assert "functionality not certified" in fixture["safe_internal_language"]
    assert "repair required" not in fixture["safe_internal_language"]
    assert "safe to operate" not in fixture["safe_internal_language"]
    assert "customer ready" not in fixture["safe_internal_language"]


def test_field_asset_outline_preserves_claim_boundaries_and_firewall() -> None:
    outline = build_aas_field_asset_visible_state_fixture_outline()
    safe = set(outline["claim_boundaries"]["safe_to_claim"])
    blocked = set(outline["claim_boundaries"]["do_not_claim_yet"])

    assert set(FIELD_ASSET_VISIBLE_STATE_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_answer_receipt",
        "authorizes_field_visit_access_recipient_or_customer_use",
        "authorizes_inspection_repair_remediation_or_maintenance",
        "certifies_functionality_safety_warranty_or_sla",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert outline["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_field_asset_outline_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)
    path = write_aas_field_asset_visible_state_fixture_outline(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_FILENAME
    assert load_aas_field_asset_visible_state_fixture_outline(artifact_dir=tmp_path)[
        "fixture_outline_id"
    ] == "execution_market.aas.field_asset_visible_state_fixture_outline.2026_06_06_0400"


def test_field_asset_outline_rejects_promoted_source_roadmap() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    roadmap["current_operator_state"]["operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator_approval_recorded"):
        build_aas_field_asset_visible_state_fixture_outline(source_roadmap=roadmap)


def test_field_asset_outline_rejects_repair_or_sla_promotion() -> None:
    outline = build_aas_field_asset_visible_state_fixture_outline()
    outline["readiness"]["outline_authorizes_inspection_repair_or_remediation"] = True

    with pytest.raises(CityOpsContractError, match="authorizes_inspection_repair_or_remediation"):
        load_aas_field_asset_visible_state_fixture_outline(
            artifact_dir=_write_fixture_triple(outline)
        )


def test_field_asset_outline_rejects_functionality_safety_or_sla_certification() -> None:
    outline = build_aas_field_asset_visible_state_fixture_outline()
    outline["readiness"]["outline_certifies_asset_functionality_safety_warranty_or_sla"] = True

    with pytest.raises(CityOpsContractError, match="certifies_asset_functionality_safety_warranty_or_sla"):
        load_aas_field_asset_visible_state_fixture_outline(
            artifact_dir=_write_fixture_triple(outline)
        )


def test_field_asset_outline_rejects_missing_visible_state_field() -> None:
    outline = build_aas_field_asset_visible_state_fixture_outline()
    outline["field_asset_visible_state_fixture_outline"]["visible_state_fields"] = [
        field
        for field in outline["field_asset_visible_state_fixture_outline"]["visible_state_fields"]
        if field != "apparent_access_or_obstruction_observed"
    ]

    with pytest.raises(CityOpsContractError, match="missing visible-state fields"):
        load_aas_field_asset_visible_state_fixture_outline(
            artifact_dir=_write_fixture_triple(outline)
        )


def test_field_asset_outline_rejects_wrong_source_row() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    for row in roadmap["roadmap_rows"]:
        if row["aas_family"] == "field_asset_ops":
            row["planning_sequence_rank"] = 5

    with pytest.raises(CityOpsContractError, match="source rank drift"):
        build_aas_field_asset_visible_state_fixture_outline(source_roadmap=roadmap)


def _write_fixture_triple(outline: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp)
    (tmp / AAS_FIELD_ASSET_VISIBLE_STATE_FIXTURE_OUTLINE_FILENAME).write_text(
        json.dumps(outline, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tmp
