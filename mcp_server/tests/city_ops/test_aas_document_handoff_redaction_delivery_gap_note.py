"""Tests for the internal/admin AAS Document Handoff redaction/delivery gap note."""

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
from mcp_server.city_ops.aas_document_handoff_redaction_delivery_gap_note import (
    AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_FILENAME,
    AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_SAFE_CLAIM,
    AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_SCHEMA,
    AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_STATUS,
    DELIVERY_PATH_UNKNOWNS,
    DOCUMENT_HANDOFF_BLOCKED_CLAIMS,
    FALSE_FLAGS,
    FORBIDDEN_LANGUAGE,
    REDACTION_CHECKS,
    build_aas_document_handoff_redaction_delivery_gap_note,
    load_aas_document_handoff_redaction_delivery_gap_note,
    write_aas_document_handoff_redaction_delivery_gap_note,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_gap_note() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_document_handoff_gap_note_matches_persisted_artifact_and_loader() -> None:
    note = build_aas_document_handoff_redaction_delivery_gap_note()

    assert note == read_gap_note()
    assert load_aas_document_handoff_redaction_delivery_gap_note() == note
    assert note["schema"] == AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_SCHEMA
    assert note["gap_note_status"] == AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_STATUS
    assert AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM in note["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_SAFE_CLAIM in note[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_document_handoff_gap_note_consumes_rank_two_roadmap_row_by_digest() -> None:
    note = build_aas_document_handoff_redaction_delivery_gap_note()
    source = note["source_roadmap"]

    assert source["file"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME
    assert source["safe_claim"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM
    assert source["consumed_row_family"] == "document_handoff"
    assert source["consumed_row_rank"] == 2
    assert len(source["digest_sha256"]) == 64


def test_document_handoff_gap_note_is_maintenance_only_not_approval_or_delivery() -> None:
    note = build_aas_document_handoff_redaction_delivery_gap_note()

    for key, expected in FALSE_FLAGS.items():
        assert note["readiness"][key] is expected
    assert note["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_decision": None,
        "recommended_no_human_posture": "maintenance_only_no_new_approval_artifact",
    }

    gap = note["document_handoff_gap_note"]
    assert gap["aas_family"] == "document_handoff"
    assert gap["allowed_use"] == "internal_admin_redaction_delivery_path_gap_note_maintenance_only"
    assert gap["maintenance_mode"] == "maintenance_only_no_new_approval_artifact"
    assert gap["still_blocked"] is True
    assert gap["next_gate_before_any_delivery_or_runtime_movement"] == (
        "separate_explicit_operator_answer_receipt_then_document_handoff_delivery_publication_gate"
    )


def test_document_handoff_gap_note_preserves_redaction_delivery_and_language_boundaries() -> None:
    note = build_aas_document_handoff_redaction_delivery_gap_note()
    gap = note["document_handoff_gap_note"]

    assert set(REDACTION_CHECKS) <= set(gap["redaction_gap_checks"])
    assert set(DELIVERY_PATH_UNKNOWNS) <= set(gap["delivery_path_unknowns"])
    assert set(FORBIDDEN_LANGUAGE) <= set(gap["forbidden_language"])
    assert "delivery path not authorized" in gap["safe_internal_language"]
    assert "custody and legal effect not claimed" in gap["safe_internal_language"]
    assert "customer ready" not in gap["safe_internal_language"]
    assert "deliver to recipient" not in gap["safe_internal_language"]
    assert "legally accepted" not in gap["safe_internal_language"]


def test_document_handoff_gap_note_preserves_claim_boundaries_and_stopped_project_firewall() -> None:
    note = build_aas_document_handoff_redaction_delivery_gap_note()
    safe = set(note["claim_boundaries"]["safe_to_claim"])
    blocked = set(note["claim_boundaries"]["do_not_claim_yet"])

    assert set(DOCUMENT_HANDOFF_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_answer_receipt",
        "creates_customer_public_or_worker_copy",
        "authorizes_recipient_channel_delivery_or_acceptance",
        "releases_exact_gps_raw_metadata_private_context_or_pii",
        "legal_notarial_custody_regulatory_or_acceptance_authority",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert note["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_document_handoff_gap_note_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)
    path = write_aas_document_handoff_redaction_delivery_gap_note(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_FILENAME
    assert load_aas_document_handoff_redaction_delivery_gap_note(artifact_dir=tmp_path)[
        "gap_note_id"
    ] == "execution_market.aas.document_handoff_redaction_delivery_gap_note.2026_06_06_0000"


def test_document_handoff_gap_note_rejects_promoted_source_roadmap() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    roadmap["current_operator_state"]["operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator_approval_recorded"):
        build_aas_document_handoff_redaction_delivery_gap_note(source_roadmap=roadmap)


def test_document_handoff_gap_note_rejects_customer_delivery_promotion() -> None:
    note = build_aas_document_handoff_redaction_delivery_gap_note()
    note["readiness"]["gap_note_authorizes_delivery_path_or_recipient"] = True

    with pytest.raises(CityOpsContractError, match="authorizes_delivery_path_or_recipient"):
        load_aas_document_handoff_redaction_delivery_gap_note(
            artifact_dir=_write_fixture_triple(note)
        )


def test_document_handoff_gap_note_rejects_missing_redaction_check() -> None:
    note = build_aas_document_handoff_redaction_delivery_gap_note()
    note["document_handoff_gap_note"]["redaction_gap_checks"] = [
        check
        for check in note["document_handoff_gap_note"]["redaction_gap_checks"]
        if check != "exclude_exact_locations_coordinates_raw_metadata_and_private_context_from_gap_note"
    ]

    with pytest.raises(CityOpsContractError, match="missing redaction checks"):
        load_aas_document_handoff_redaction_delivery_gap_note(
            artifact_dir=_write_fixture_triple(note)
        )


def test_document_handoff_gap_note_rejects_wrong_source_row() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    for row in roadmap["roadmap_rows"]:
        if row["aas_family"] == "document_handoff":
            row["planning_sequence_rank"] = 4

    with pytest.raises(CityOpsContractError, match="source rank drift"):
        build_aas_document_handoff_redaction_delivery_gap_note(source_roadmap=roadmap)


def _write_fixture_triple(note: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp)
    (tmp / AAS_DOCUMENT_HANDOFF_REDACTION_DELIVERY_GAP_NOTE_FILENAME).write_text(
        json.dumps(note, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tmp
