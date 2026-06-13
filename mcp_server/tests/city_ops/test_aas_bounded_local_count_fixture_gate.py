"""Tests for the internal/admin AAS Bounded Local Count fixture gate."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_bounded_local_count_fixture_gate import (
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_BLOCKED_CLAIMS,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SCHEMA,
    AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_STATUS,
    ALLOWED_COUNT_METHODS,
    ALLOWED_PACKET_SCHEMA,
    ALLOWED_PACKET_STATUS,
    BOUNDING_RULES,
    FALSE_FLAGS,
    REQUIRED_BLOCKED_CLAIMS,
    REQUIRED_PACKET_FIELDS,
    SOURCE_CONTRACT_SAFE_CLAIM,
    build_aas_bounded_local_count_fixture_gate,
    load_aas_bounded_local_count_fixture_gate,
    sample_valid_bounded_local_count_packet,
    validate_bounded_local_count_packet,
    write_aas_bounded_local_count_fixture_gate,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_gate() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_bounded_local_count_gate_matches_persisted_artifact_and_loader() -> None:
    gate = build_aas_bounded_local_count_fixture_gate()

    assert gate == read_gate()
    assert load_aas_bounded_local_count_fixture_gate() == gate
    assert gate["schema"] == AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SCHEMA
    assert gate["gate_status"] == AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_STATUS
    assert SOURCE_CONTRACT_SAFE_CLAIM in gate["claim_boundaries"]["safe_to_claim"]
    assert AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_SAFE_CLAIM in gate["claim_boundaries"][
        "safe_to_claim"
    ]


def test_bounded_local_count_gate_preserves_contract_shape() -> None:
    gate = build_aas_bounded_local_count_fixture_gate()
    schema = gate["fixture_schema"]

    assert schema["required_fields"] == REQUIRED_PACKET_FIELDS
    assert schema["allowed_packet_schema"] == ALLOWED_PACKET_SCHEMA
    assert schema["allowed_packet_status"] == ALLOWED_PACKET_STATUS
    assert schema["allowed_count_methods"] == ALLOWED_COUNT_METHODS
    assert set(REQUIRED_BLOCKED_CLAIMS) <= set(schema["required_blocked_claims"])
    assert set(BOUNDING_RULES) <= set(schema["bounding_rules"])
    assert len(gate["source_contract"]["digest_sha256"]) == 64
    assert len(gate["sample_internal_fixture_packet_digest_sha256"]) == 64


def test_bounded_local_count_gate_records_no_answer_approval_collection_or_exposure() -> None:
    gate = build_aas_bounded_local_count_fixture_gate()

    for key, expected in FALSE_FLAGS.items():
        assert gate["readiness"][key] is expected
    assert gate["current_operator_state"] == {
        "explicit_operator_answer_available": False,
        "operator_approval_recorded": False,
        "answer_receipt_created": False,
        "collection_authorized": False,
        "selected_decision": None,
        "recommended_posture": "pause_aas_proof_layering",
    }
    assert gate["stopped_project_firewall"] == {
        "source": "DREAM-PRIORITIES.md explicit stop list",
        "autojob_work_allowed": False,
        "frontier_academy_work_allowed": False,
        "kk_v2_work_allowed": False,
        "karmacadabra_v2_work_allowed": False,
    }


def test_bounded_local_count_gate_preserves_claim_boundaries() -> None:
    gate = build_aas_bounded_local_count_fixture_gate()
    safe = set(gate["claim_boundaries"]["safe_to_claim"])
    blocked = set(gate["claim_boundaries"]["do_not_claim_yet"])

    assert set(AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "authorizes_collection_site_access_or_worker_tasking",
        "creates_customer_public_or_worker_copy",
        "catalog_pricing_quote_route_queue_or_dispatch",
        "claims_representativeness_statistical_validity_or_certification",
        "emits_erc8004_reputation_or_worker_skill_dna",
        "releases_exact_location_raw_metadata_private_context_or_pii",
        "integrates_or_expands_stopped_projects",
    ]:
        assert any(fragment in claim for claim in blocked)
        assert not any(fragment in claim for claim in safe)


def test_bounded_local_count_packet_validator_accepts_internal_sample() -> None:
    packet = sample_valid_bounded_local_count_packet()

    assert validate_bounded_local_count_packet(packet) == packet


def test_bounded_local_count_packet_rejects_unbounded_question() -> None:
    packet = sample_valid_bounded_local_count_packet()
    packet["count_question"] = "Count every citywide queue continuously."

    with pytest.raises(CityOpsContractError, match="citywide"):
        validate_bounded_local_count_packet(packet)


def test_bounded_local_count_packet_rejects_missing_coverage_limits() -> None:
    packet = sample_valid_bounded_local_count_packet()
    packet["coverage_limits"] = []

    with pytest.raises(CityOpsContractError, match="coverage limits"):
        validate_bounded_local_count_packet(packet)


def test_bounded_local_count_packet_rejects_missing_uncertainty() -> None:
    packet = sample_valid_bounded_local_count_packet()
    packet["uncertainty_statement"] = "Exact certified count."

    with pytest.raises(CityOpsContractError, match="certified count"):
        validate_bounded_local_count_packet(packet)


def test_bounded_local_count_packet_rejects_raw_location_metadata() -> None:
    packet = sample_valid_bounded_local_count_packet()
    packet["place_boundary"] = "latitude and longitude pair"

    with pytest.raises(CityOpsContractError, match="latitude"):
        validate_bounded_local_count_packet(packet)


def test_bounded_local_count_packet_rejects_customer_or_dispatch_readiness() -> None:
    packet = sample_valid_bounded_local_count_packet()
    packet["readiness"] = {"dispatch_ready": True}

    with pytest.raises(CityOpsContractError, match="dispatch_ready"):
        validate_bounded_local_count_packet(packet)


def test_bounded_local_count_packet_rejects_stopped_project_integration() -> None:
    packet = sample_valid_bounded_local_count_packet()
    packet["notes"] = "Connect this to AutoJob matching."

    with pytest.raises(CityOpsContractError, match="autojob"):
        validate_bounded_local_count_packet(packet)


def test_bounded_local_count_packet_rejects_missing_blocked_claim() -> None:
    packet = sample_valid_bounded_local_count_packet()
    packet["blocked_claims_snapshot"] = [
        claim
        for claim in packet["blocked_claims_snapshot"]
        if claim != "payment_production_change"
    ]

    with pytest.raises(CityOpsContractError, match="payment_production_change"):
        validate_bounded_local_count_packet(packet)


def test_bounded_local_count_gate_rejects_promoted_readiness(tmp_path: Path) -> None:
    gate = copy.deepcopy(build_aas_bounded_local_count_fixture_gate())
    gate["readiness"]["gate_launches_dispatch_or_worker_instruction"] = True
    (tmp_path / AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME).write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(CityOpsContractError, match="gate_launches_dispatch"):
        load_aas_bounded_local_count_fixture_gate(artifact_dir=tmp_path)


def test_bounded_local_count_gate_write_roundtrip(tmp_path: Path) -> None:
    path = write_aas_bounded_local_count_fixture_gate(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_FILENAME
    assert load_aas_bounded_local_count_fixture_gate(artifact_dir=tmp_path)["gate_id"] == (
        "execution_market.aas.bounded_local_count.fixture_gate.2026_06_13_0000"
    )
