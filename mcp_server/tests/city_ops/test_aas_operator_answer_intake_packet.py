"""Tests for the AAS operator answer intake packet."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_operator_answer_intake_packet import (
    AAS_OPERATOR_ANSWER_INTAKE_PACKET_FILENAME,
    AAS_OPERATOR_ANSWER_INTAKE_PACKET_SAFE_CLAIM,
    AAS_OPERATOR_ANSWER_INTAKE_PACKET_SCHEMA,
    AAS_OPERATOR_ANSWER_INTAKE_PACKET_STATUS,
    INTAKE_PACKET_BLOCKED_CLAIMS,
    INTAKE_PACKET_FALSE_FLAGS,
    build_aas_operator_answer_intake_packet,
    load_aas_operator_answer_intake_packet,
    write_aas_operator_answer_intake_packet,
)
from mcp_server.city_ops.aas_operator_answer_receipt_gate import (
    DISALLOWED_OPERATOR_REFERENCE_PATTERNS,
    NEXT_REQUIRED_GATE_BY_VALUE,
    RECEIPT_REQUIRED_FIELDS,
    load_aas_operator_answer_receipt_gate,
)
from mcp_server.city_ops.aas_two_lane_operator_answer_schema import (
    ALLOWED_FUTURE_DECISIONS,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_packet() -> dict:
    return json.loads(
        (ARTIFACT_DIR / AAS_OPERATOR_ANSWER_INTAKE_PACKET_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def seed_sources(tmp_path: Path) -> None:
    for source in ARTIFACT_DIR.glob("*.json"):
        shutil.copy(source, tmp_path / source.name)


def test_answer_intake_packet_matches_persisted_artifact_and_loader() -> None:
    packet = build_aas_operator_answer_intake_packet()

    assert packet == read_packet()
    assert load_aas_operator_answer_intake_packet() == packet
    assert packet["schema"] == AAS_OPERATOR_ANSWER_INTAKE_PACKET_SCHEMA
    assert packet["packet_status"] == AAS_OPERATOR_ANSWER_INTAKE_PACKET_STATUS
    assert AAS_OPERATOR_ANSWER_INTAKE_PACKET_SAFE_CLAIM in packet["claim_boundaries"][
        "safe_to_claim"
    ]


def test_answer_intake_packet_consumes_receipt_gate_without_selecting_answer() -> None:
    packet = build_aas_operator_answer_intake_packet()
    contract = packet["one_answer_intake_contract"]

    assert packet["source_gate"]["file"] == "aas_operator_answer_receipt_gate.json"
    assert len(packet["source_gate"]["digest_sha256"]) == 64
    assert contract["one_answer_only"] is True
    assert contract["template_is_not_receipt"] is True
    assert contract["template_records_no_current_answer"] is True
    assert contract["future_receipt_required_fields"] == RECEIPT_REQUIRED_FIELDS
    assert [item["value"] for item in contract["allowed_operator_answer_values"]] == ALLOWED_FUTURE_DECISIONS
    for item in contract["allowed_operator_answer_values"]:
        assert item["selected_by_this_packet"] is False
        assert item["approval_granted_by_this_packet"] is False
        assert item["next_required_gate_if_explicitly_chosen"] == NEXT_REQUIRED_GATE_BY_VALUE[
            item["value"]
        ]


def test_answer_intake_packet_preserves_reference_redaction_rules() -> None:
    packet = build_aas_operator_answer_intake_packet()
    rules = packet["one_answer_intake_contract"]["operator_reference_rules"]
    template = packet["one_answer_intake_contract"]["future_receipt_template"]

    assert rules["required"] is True
    assert rules["must_be_opaque_non_secret_non_doxxing"] is True
    assert rules["disallowed_material"] == sorted(DISALLOWED_OPERATOR_REFERENCE_PATTERNS.keys())
    assert template["explicit_operator_reference"] == "<opaque_non_secret_reference_no_pii_no_secret>"
    assert template["approved_sections"] == []
    assert template["delivery_path_authorized"] is False
    assert template["runtime_path_authorized"] is False
    assert template["blocked_claims_preserved"] == packet["still_blocked_claims"]


def test_answer_intake_packet_keeps_stopped_project_firewall_closed() -> None:
    packet = build_aas_operator_answer_intake_packet()
    firewall = packet["dream_priority_firewall"]

    assert firewall["first_read"] == "DREAM-PRIORITIES.md"
    assert firewall["active_focus"] == "Execution Market AAS / City-as-a-Service only"
    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert "ignore AutoJob" in firewall["stale_payload_policy"]


def test_answer_intake_packet_preserves_claim_boundaries_and_false_flags() -> None:
    packet = build_aas_operator_answer_intake_packet()
    safe = set(packet["claim_boundaries"]["safe_to_claim"])
    blocked = set(packet["claim_boundaries"]["do_not_claim_yet"])

    assert set(INTAKE_PACKET_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for key, expected in INTAKE_PACKET_FALSE_FLAGS.items():
        assert packet["readiness"][key] is expected


def test_answer_intake_packet_write_and_load_round_trip(tmp_path: Path) -> None:
    seed_sources(tmp_path)

    path = write_aas_operator_answer_intake_packet(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_OPERATOR_ANSWER_INTAKE_PACKET_FILENAME
    assert load_aas_operator_answer_intake_packet(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_answer_intake_packet_fails_closed_if_source_gate_promotes_answer() -> None:
    gate = copy.deepcopy(load_aas_operator_answer_receipt_gate())
    gate["readiness"]["operator_answer_recorded"] = True

    with pytest.raises(CityOpsContractError, match="operator_answer_recorded"):
        build_aas_operator_answer_intake_packet(source_gate=gate)


def test_answer_intake_packet_fails_closed_if_value_is_selected() -> None:
    gate = copy.deepcopy(load_aas_operator_answer_receipt_gate())
    gate["allowed_operator_answer_values"][0]["selected_by_this_gate"] = True

    with pytest.raises(CityOpsContractError, match="selected an answer"):
        build_aas_operator_answer_intake_packet(source_gate=gate)


def test_answer_intake_packet_loader_fails_closed_on_stopped_project_promotion(
    tmp_path: Path,
) -> None:
    seed_sources(tmp_path)
    path = write_aas_operator_answer_intake_packet(artifact_dir=tmp_path)
    packet = json.loads(path.read_text(encoding="utf-8"))
    packet["dream_priority_firewall"]["autojob_work_allowed"] = True
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="autojob_work_allowed"):
        load_aas_operator_answer_intake_packet(artifact_dir=tmp_path)
