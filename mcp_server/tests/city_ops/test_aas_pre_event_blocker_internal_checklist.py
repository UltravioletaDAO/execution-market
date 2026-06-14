"""Tests for the internal/admin Pre-Event Blocker Check checklist menu."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_concept_gap_implementation_roadmap import (
    write_aas_concept_gap_implementation_roadmap,
)
from mcp_server.city_ops.aas_concept_gap_matrix import write_aas_concept_gap_matrix
from mcp_server.city_ops.aas_event_readiness_observation_outline import (
    AAS_EVENT_READINESS_OBSERVATION_OUTLINE_FILENAME,
    AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM,
    EVENT_READINESS_OBSERVATION_BLOCKED_CLAIMS,
    build_aas_event_readiness_observation_outline,
    write_aas_event_readiness_observation_outline,
)
from mcp_server.city_ops.aas_pre_event_blocker_internal_checklist import (
    AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_FILENAME,
    AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SAFE_CLAIM,
    AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SCHEMA,
    AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_STATUS,
    CHECKLIST_ROWS,
    FALSE_FLAGS,
    PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_BLOCKED_CLAIMS,
    REQUIRED_CHECK_CODES,
    build_aas_pre_event_blocker_internal_checklist,
    load_aas_pre_event_blocker_internal_checklist,
    write_aas_pre_event_blocker_internal_checklist,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_checklist() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_pre_event_blocker_checklist_matches_persisted_artifact_and_loader() -> None:
    checklist = build_aas_pre_event_blocker_internal_checklist()

    assert checklist == read_checklist()
    assert load_aas_pre_event_blocker_internal_checklist() == checklist
    assert checklist["schema"] == AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SCHEMA
    assert checklist["checklist_status"] == AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_STATUS
    assert AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM in checklist[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_SAFE_CLAIM in checklist[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_pre_event_blocker_checklist_consumes_event_outline_by_digest() -> None:
    checklist = build_aas_pre_event_blocker_internal_checklist()
    source = checklist["source_outline"]

    assert source["file"] == AAS_EVENT_READINESS_OBSERVATION_OUTLINE_FILENAME
    assert source["safe_claim"] == AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM
    assert source["consumed_family"] == "event_readiness"
    assert source["canonical_family"] == "Pre-Event Blocker Check"
    assert len(source["digest_sha256"]) == 64


def test_pre_event_blocker_checklist_is_held_internal_admin_only() -> None:
    checklist = build_aas_pre_event_blocker_internal_checklist()

    for key, expected in FALSE_FLAGS.items():
        assert checklist["readiness"][key] is expected
    assert checklist["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "event_type_selected": False,
        "collection_method_authorized": False,
        "selected_decision": None,
        "recommended_no_human_posture": "checklist_only",
    }

    body = checklist["pre_event_blocker_internal_checklist"]
    assert body["canonical_family"] == "Pre-Event Blocker Check"
    assert body["legacy_source_family"] == "event_readiness"
    assert body["allowed_use"] == (
        "internal_admin_checklist_only_no_event_type_no_site_access_no_customer_copy"
    )
    assert body["checklist_mode"] == "checklist_only"
    assert body["still_blocked"] is True
    assert body["next_gate_before_any_delivery_or_runtime_movement"] == (
        "separate_event_type_observation_window_and_operator_answer_receipt"
    )


def test_pre_event_blocker_checklist_rows_preserve_required_codes_and_truth_families() -> None:
    checklist = build_aas_pre_event_blocker_internal_checklist()
    body = checklist["pre_event_blocker_internal_checklist"]
    rows = body["checklist_rows"]

    assert rows == CHECKLIST_ROWS
    assert [row["check_code"] for row in rows] == REQUIRED_CHECK_CODES
    assert body["required_check_codes"] == REQUIRED_CHECK_CODES
    assert set(body["allowed_truth_families"]) == {
        "operator_truth",
        "surface_truth",
        "runtime_truth",
        "location_privacy_truth",
        "authority_truth",
    }
    for row in rows:
        assert row["allowed_check_values"]
        assert row["safe_internal_read"]
        assert row["forbidden_promotion"].startswith("does_not_")
        assert row["missing_truth_family"] in body["allowed_truth_families"]


def test_pre_event_blocker_checklist_preserves_claim_boundaries_and_firewall() -> None:
    checklist = build_aas_pre_event_blocker_internal_checklist()
    safe = set(checklist["claim_boundaries"]["safe_to_claim"])
    blocked = set(checklist["claim_boundaries"]["do_not_claim_yet"])

    assert set(EVENT_READINESS_OBSERVATION_BLOCKED_CLAIMS) <= blocked
    assert set(PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_answer_receipt",
        "selects_event_type_future_answer_or_collection_method",
        "authorizes_event_site_access_recipient_or_customer_use",
        "authorizes_permit_security_vendor_venue_or_crowd_control_decision",
        "certifies_capacity_safety_attendance_outcome_or_sla",
        "releases_exact_gps_raw_metadata_private_context_or_pii",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert checklist["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_pre_event_blocker_checklist_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)
    write_aas_event_readiness_observation_outline(artifact_dir=tmp_path)
    path = write_aas_pre_event_blocker_internal_checklist(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_FILENAME
    assert load_aas_pre_event_blocker_internal_checklist(artifact_dir=tmp_path)[
        "checklist_id"
    ] == "execution_market.aas.pre_event_blocker_internal_checklist.2026_06_14_0200"


def test_pre_event_blocker_checklist_rejects_promoted_source_outline() -> None:
    outline = copy.deepcopy(build_aas_event_readiness_observation_outline())
    outline["readiness"]["outline_authorizes_permit_security_vendor_or_venue_decision"] = True

    with pytest.raises(CityOpsContractError, match="source readiness promoted"):
        build_aas_pre_event_blocker_internal_checklist(source_outline=outline)


def test_pre_event_blocker_checklist_rejects_event_type_selection() -> None:
    checklist = build_aas_pre_event_blocker_internal_checklist()
    checklist["current_operator_state"]["event_type_selected"] = True

    with pytest.raises(CityOpsContractError, match="event_type_selected"):
        load_aas_pre_event_blocker_internal_checklist(artifact_dir=_write_fixture_quad(checklist))


def test_pre_event_blocker_checklist_rejects_missing_required_check_code() -> None:
    checklist = build_aas_pre_event_blocker_internal_checklist()
    rows = checklist["pre_event_blocker_internal_checklist"]["checklist_rows"]
    checklist["pre_event_blocker_internal_checklist"]["checklist_rows"] = [
        row for row in rows if row["check_code"] != "time_window_warning_state"
    ]

    with pytest.raises(CityOpsContractError, match="code drift"):
        load_aas_pre_event_blocker_internal_checklist(artifact_dir=_write_fixture_quad(checklist))


def test_pre_event_blocker_checklist_rejects_dispatch_or_privacy_promotion() -> None:
    checklist = build_aas_pre_event_blocker_internal_checklist()
    checklist["readiness"]["checklist_creates_catalog_pricing_quote_route_queue_or_dispatch"] = True

    with pytest.raises(CityOpsContractError, match="catalog_pricing_quote_route_queue_or_dispatch"):
        load_aas_pre_event_blocker_internal_checklist(artifact_dir=_write_fixture_quad(checklist))

    checklist = build_aas_pre_event_blocker_internal_checklist()
    checklist["readiness"]["checklist_releases_exact_gps_raw_metadata_private_context_or_pii"] = True

    with pytest.raises(CityOpsContractError, match="raw_metadata_private_context_or_pii"):
        load_aas_pre_event_blocker_internal_checklist(artifact_dir=_write_fixture_quad(checklist))


def _write_fixture_quad(checklist: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp)
    write_aas_event_readiness_observation_outline(artifact_dir=tmp)
    (tmp / AAS_PRE_EVENT_BLOCKER_INTERNAL_CHECKLIST_FILENAME).write_text(
        json.dumps(checklist, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tmp
