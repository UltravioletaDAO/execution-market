"""Tests for the internal/admin AAS Local Data Collection measurement rubric."""

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
from mcp_server.city_ops.aas_local_data_collection_measurement_uncertainty_rubric import (
    AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_FILENAME,
    AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_SAFE_CLAIM,
    AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_SCHEMA,
    AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_STATUS,
    FALSE_FLAGS,
    FORBIDDEN_LANGUAGE,
    LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_BLOCKED_CLAIMS,
    MEASUREMENT_UNCERTAINTY_FIELDS,
    RUBRIC_BOUNDARIES,
    build_aas_local_data_collection_measurement_uncertainty_rubric,
    load_aas_local_data_collection_measurement_uncertainty_rubric,
    write_aas_local_data_collection_measurement_uncertainty_rubric,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_fixture_rubric() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_local_data_collection_rubric_matches_persisted_artifact_and_loader() -> None:
    rubric = build_aas_local_data_collection_measurement_uncertainty_rubric()

    assert rubric == read_fixture_rubric()
    assert load_aas_local_data_collection_measurement_uncertainty_rubric() == rubric
    assert rubric["schema"] == AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_SCHEMA
    assert rubric["rubric_status"] == AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_STATUS
    assert AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM in rubric["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_SAFE_CLAIM in rubric[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_local_data_collection_rubric_consumes_rank_seven_roadmap_row_by_digest() -> None:
    rubric = build_aas_local_data_collection_measurement_uncertainty_rubric()
    source = rubric["source_roadmap"]

    assert source["file"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME
    assert source["safe_claim"] == AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM
    assert source["consumed_row_family"] == "local_data_collection"
    assert source["consumed_row_rank"] == 7
    assert len(source["digest_sha256"]) == 64


def test_local_data_collection_rubric_is_planning_only_not_dataset_or_dispatch() -> None:
    rubric = build_aas_local_data_collection_measurement_uncertainty_rubric()

    for key, expected in FALSE_FLAGS.items():
        assert rubric["readiness"][key] is expected
    assert rubric["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "selected_decision": None,
        "recommended_no_human_posture": "planning_only_no_fixture_promotion",
    }

    fixture = rubric["local_data_collection_measurement_uncertainty_rubric"]
    assert fixture["aas_family"] == "local_data_collection"
    assert fixture["allowed_use"] == (
        "internal_admin_measurement_uncertainty_rubric_outline_no_dataset_publication"
    )
    assert fixture["planning_mode"] == "planning_only_no_fixture_promotion"
    assert fixture["still_blocked"] is True
    assert fixture["next_gate_before_any_delivery_or_runtime_movement"] == (
        "separate_explicit_operator_answer_receipt_then_local_data_collection_customer_or_dispatch_gate"
    )


def test_local_data_collection_rubric_preserves_measurement_uncertainty_boundaries() -> None:
    rubric = build_aas_local_data_collection_measurement_uncertainty_rubric()
    fixture = rubric["local_data_collection_measurement_uncertainty_rubric"]

    assert set(MEASUREMENT_UNCERTAINTY_FIELDS) <= set(
        fixture["measurement_uncertainty_fields"]
    )
    assert set(RUBRIC_BOUNDARIES) <= set(fixture["rubric_boundaries"])
    assert set(FORBIDDEN_LANGUAGE) <= set(fixture["forbidden_language"])
    assert "local data collection measurement uncertainty rubric only" in fixture[
        "safe_internal_language"
    ]
    assert "dataset publication and measurement certification blocked" in fixture[
        "safe_internal_language"
    ]
    assert "observed values require uncertainty and missingness context" in fixture[
        "safe_internal_language"
    ]
    assert "dataset published" not in fixture["safe_internal_language"]
    assert "measurement certified" not in fixture["safe_internal_language"]
    assert "accuracy guaranteed" not in fixture["safe_internal_language"]
    assert "dispatch ready" not in fixture["safe_internal_language"]


def test_local_data_collection_rubric_preserves_claim_boundaries_and_firewall() -> None:
    rubric = build_aas_local_data_collection_measurement_uncertainty_rubric()
    safe = set(rubric["claim_boundaries"]["safe_to_claim"])
    blocked = set(rubric["claim_boundaries"]["do_not_claim_yet"])

    assert set(LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "creates_answer_receipt",
        "authorizes_data_collection_site_access_recipient_or_customer_use",
        "authorizes_sensor_deployment_survey_sampling_or_worker_collection",
        "certifies_measurement_accuracy_completeness_or_statistical_validity",
        "publishes_dataset_report_dashboard_or_benchmark",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)

    assert rubric["governing_priority"]["stopped_project_firewall"] == {
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_local_data_collection_rubric_write_roundtrip(tmp_path: Path) -> None:
    write_aas_concept_gap_matrix(artifact_dir=tmp_path)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp_path)
    path = write_aas_local_data_collection_measurement_uncertainty_rubric(
        artifact_dir=tmp_path
    )

    assert path == tmp_path / AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_FILENAME
    assert load_aas_local_data_collection_measurement_uncertainty_rubric(
        artifact_dir=tmp_path
    )["rubric_id"] == (
        "execution_market.aas.local_data_collection.measurement_uncertainty_rubric.2026_06_06_2300"
    )


def test_local_data_collection_rubric_rejects_promoted_source_roadmap() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    roadmap["current_operator_state"]["operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator_approval_recorded"):
        build_aas_local_data_collection_measurement_uncertainty_rubric(
            source_roadmap=roadmap
        )


def test_local_data_collection_rubric_rejects_dataset_publication() -> None:
    rubric = build_aas_local_data_collection_measurement_uncertainty_rubric()
    rubric["readiness"]["rubric_publishes_dataset_report_dashboard_or_benchmark"] = True

    with pytest.raises(CityOpsContractError, match="publishes_dataset_report_dashboard_or_benchmark"):
        load_aas_local_data_collection_measurement_uncertainty_rubric(
            artifact_dir=_write_fixture_triple(rubric)
        )


def test_local_data_collection_rubric_rejects_measurement_certification() -> None:
    rubric = build_aas_local_data_collection_measurement_uncertainty_rubric()
    rubric["readiness"][
        "rubric_certifies_measurement_accuracy_completeness_or_statistical_validity"
    ] = True

    with pytest.raises(CityOpsContractError, match="certifies_measurement_accuracy_completeness_or_statistical_validity"):
        load_aas_local_data_collection_measurement_uncertainty_rubric(
            artifact_dir=_write_fixture_triple(rubric)
        )


def test_local_data_collection_rubric_rejects_missing_uncertainty_field() -> None:
    rubric = build_aas_local_data_collection_measurement_uncertainty_rubric()
    rubric["local_data_collection_measurement_uncertainty_rubric"][
        "measurement_uncertainty_fields"
    ] = [
        field
        for field in rubric["local_data_collection_measurement_uncertainty_rubric"][
            "measurement_uncertainty_fields"
        ]
        if field != "uncertainty_range_or_confidence_caveat_required"
    ]

    with pytest.raises(CityOpsContractError, match="missing measurement uncertainty fields"):
        load_aas_local_data_collection_measurement_uncertainty_rubric(
            artifact_dir=_write_fixture_triple(rubric)
        )


def test_local_data_collection_rubric_rejects_wrong_source_row() -> None:
    roadmap = copy.deepcopy(build_aas_concept_gap_implementation_roadmap())
    for row in roadmap["roadmap_rows"]:
        if row["aas_family"] == "local_data_collection":
            row["planning_sequence_rank"] = 8

    with pytest.raises(CityOpsContractError, match="source rank drift"):
        build_aas_local_data_collection_measurement_uncertainty_rubric(
            source_roadmap=roadmap
        )


def _write_fixture_triple(rubric: dict) -> Path:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    write_aas_concept_gap_matrix(artifact_dir=tmp)
    write_aas_concept_gap_implementation_roadmap(artifact_dir=tmp)
    (tmp / AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_FILENAME).write_text(
        json.dumps(rubric, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tmp
