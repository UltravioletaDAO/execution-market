"""Tests for the internal/admin AAS Event Readiness observation outline."""

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
from mcp_server.city_ops.aas_event_readiness_observation_outline import (
    AAS_EVENT_READINESS_OBSERVATION_OUTLINE_FILENAME,
    AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM,
    AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SCHEMA,
    AAS_EVENT_READINESS_OBSERVATION_OUTLINE_STATUS,
    EVENT_READINESS_OBSERVATION_BLOCKED_CLAIMS,
    FALSE_FLAGS,
    FORBIDDEN_LANGUAGE,
    OBSERVATION_BOUNDARIES,
    OBSERVATION_FIELDS,
    build_aas_event_readiness_observation_outline,
    load_aas_event_readiness_observation_outline,
    write_aas_event_readiness_observation_outline,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture_outline() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_EVENT_READINESS_OBSERVATION_OUTLINE_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_event_readiness_outline_matches_persisted_artifact_and_loader() -> None:
    outline = build_aas_event_readiness_observation_outline()

    assert outline == read_fixture_outline()
    assert load_aas_event_readiness_observation_outline() == outline
    assert outline["schema"] == AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SCHEMA
    assert outline["observation_outline_status"] == AAS_EVENT_READINESS_OBSERVATION_OUTLINE_STATUS
    assert AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM in outline["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_EVENT_READINESS_OBSERVATION_OUTLINE_SAFE_CLAIM in outline[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_event_readiness_outline_consumes_rank_five_roadmap_row_by_digest() -> None:
    outline = build_aas_event_readiness_observation_outline()
    source = outline["source_roadmap"]

    assert source["file"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME
    assert source["safe_claim"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM
    assert source["consumed_row_family"] == "event_readiness"
    assert source["consumed_row_rank"] == 5
    assert len(source["digest_sha256"]) == 64


def test_event_readiness_outline_is_concept_only_not_permit_security_or_dispatch() -> None:
    outline = build_aas_event_readiness_observation_outline()

    for key, expected in FALSE_FLAGS.items():
        assert outline["readiness"][key] is expected
    assert outline["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_decision": None,
        "recommended_no_human_posture": "concept_outline_only",
    }

    fixture = outline["event_readiness_observation_outline"]
    assert fixture["aas_family"] == "event_readiness"
    assert fixture["allowed_use"] == (
        "internal_admin_observed_pre_event_blocker_outline_no_permit_security_or_outcome_claim"
    )
    assert fixture["concept_mode"] == "concept_outline_only"
    assert fixture["still_blocked"] is True
    assert fixture["next_gate_before_any_delivery_or_runtime_movement"] == (
        "separate_explicit_operator_answer_receipt_then_event_readiness_customer_or_dispatch_gate"
    )


def test_event_readiness_outline_preserves_observation_and_language_boundaries() -> None:
    outline = build_aas_event_readiness_observation_outline()
    fixture = outline["event_readiness_observation_outline"]

    assert set(OBSERVATION_FIELDS) <= set(fixture["observation_fields"])
    assert set(OBSERVATION_BOUNDARIES) <= set(fixture["observation_boundaries"])
    assert set(FORBIDDEN_LANGUAGE) <= set(fixture["forbidden_language"])
    assert "visible event-readiness observation outline only" in fixture["safe_internal_language"]
    assert "permit security and outcome claims blocked" in fixture["safe_internal_language"]
    assert "visible setup does not certify operational readiness" in fixture[
        "safe_internal_language"
    ]
    assert "permit approved" not in fixture["safe_internal_language"]
    assert "security cleared" not in fixture["safe_internal_language"]
    assert "event guaranteed" not in fixture["safe_internal_language"]
    assert "dispatch ready" not in fixture["safe_internal_language"]


def test_event_readiness_outline_preserves_claim_boundaries_and_firewall() -> None:
    outline = build_aas_event_readiness_observation_outline()
    safe = set(outline["claim_boundaries"]["safe_to_claim"])
    blocked = set(outline["claim_boundaries"]["do_not_claim_yet"])

    assert set(EVENT_READINESS_OBSERVATION_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_answer_receipt",
        "authorizes_event_site_access_recipient_or_customer_use",
        "authorizes_permit_security_vendor_venue_or_crowd_control_decision",
        "certifies_capacity_safety_attendance_outcome_or_sla",
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


def test_event_readiness_outline_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)
    path = write_aas_event_readiness_observation_outline(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_EVENT_READINESS_OBSERVATION_OUTLINE_FILENAME
    assert load_aas_event_readiness_observation_outline(artifact_dir=tmp_path)[
        "observation_outline_id"
    ] == "execution_market.aas.event_readiness_observation_outline.2026_06_06_0700"


def test_event_readiness_outline_rejects_promoted_source_roadmap() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    roadmap["current_operator_state"]["operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator_approval_recorded"):
        build_aas_event_readiness_observation_outline(source_roadmap=roadmap)


def test_event_readiness_outline_rejects_permit_or_security_promotion() -> None:
    outline = build_aas_event_readiness_observation_outline()
    outline["readiness"]["outline_authorizes_permit_security_vendor_or_venue_decision"] = True

    with pytest.raises(CityOpsContractError, match="authorizes_permit_security_vendor_or_venue_decision"):
        load_aas_event_readiness_observation_outline(artifact_dir=_write_fixture_triple(outline))


def test_event_readiness_outline_rejects_capacity_safety_or_outcome_certification() -> None:
    outline = build_aas_event_readiness_observation_outline()
    outline["readiness"]["outline_certifies_capacity_safety_attendance_outcome_or_sla"] = True

    with pytest.raises(CityOpsContractError, match="certifies_capacity_safety_attendance_outcome_or_sla"):
        load_aas_event_readiness_observation_outline(artifact_dir=_write_fixture_triple(outline))


def test_event_readiness_outline_rejects_missing_observation_field() -> None:
    outline = build_aas_event_readiness_observation_outline()
    outline["event_readiness_observation_outline"]["observation_fields"] = [
        field
        for field in outline["event_readiness_observation_outline"]["observation_fields"]
        if field != "apparent_staging_or_wayfinding_state_observed"
    ]

    with pytest.raises(CityOpsContractError, match="missing observation fields"):
        load_aas_event_readiness_observation_outline(artifact_dir=_write_fixture_triple(outline))


def test_event_readiness_outline_rejects_wrong_source_row() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    for row in roadmap["roadmap_rows"]:
        if row["aas_family"] == "event_readiness":
            row["planning_sequence_rank"] = 6

    with pytest.raises(CityOpsContractError, match="source rank drift"):
        build_aas_event_readiness_observation_outline(source_roadmap=roadmap)


def _write_fixture_triple(outline: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp)
    (tmp / AAS_EVENT_READINESS_OBSERVATION_OUTLINE_FILENAME).write_text(
        json.dumps(outline, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tmp
