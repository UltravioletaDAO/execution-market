import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_three_family_packaging_review_packet import (
    AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME,
    AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM,
    AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SCHEMA,
    PACKET_BLOCKED_CLAIMS,
    PACKET_ID,
    READINESS_FALSE_FLAGS,
    REVIEW_MODE,
    SOURCE_DECISION_SPECS,
    build_aas_three_family_packaging_review_packet,
    load_aas_three_family_packaging_review_packet,
    write_aas_three_family_packaging_review_packet,
)
from mcp_server.city_ops.compliance_desk_sample_output_review_decision import (
    build_compliance_desk_sample_output_review_decision,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.document_handoff_sample_output_review_decision import (
    build_document_handoff_sample_output_review_decision,
)
from mcp_server.city_ops.incident_verification_sample_output_review_decision import (
    build_incident_verification_sample_output_review_decision,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_packet() -> dict:
    with (ARTIFACT_DIR / AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def source_decisions() -> dict:
    return {
        "compliance_desk": build_compliance_desk_sample_output_review_decision(),
        "document_handoff": build_document_handoff_sample_output_review_decision(),
        "incident_verification": build_incident_verification_sample_output_review_decision(),
    }


def test_packaging_review_packet_matches_persisted_artifact():
    packet = build_aas_three_family_packaging_review_packet()

    assert packet == read_packet()
    assert load_aas_three_family_packaging_review_packet() == packet
    assert packet["schema"] == AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SCHEMA
    assert packet["packet_id"] == PACKET_ID
    assert packet["review_mode"] == REVIEW_MODE
    assert AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_SAFE_CLAIM in packet["safe_to_claim"]


def test_packet_consumes_exactly_three_explicit_hold_decisions():
    packet = build_aas_three_family_packaging_review_packet()

    assert packet["source_decision_files"] == [spec["source_file"] for spec in SOURCE_DECISION_SPECS]
    assert len(packet["source_decisions"]) == 3
    assert len(packet["review_rows"]) == 3
    assert packet["summary"]["families_reviewed"] == 3
    assert packet["summary"]["all_families_at_explicit_hold_decision"] is True
    assert packet["summary"]["all_customer_delivery_blocked"] is True
    assert packet["summary"]["all_publication_blocked"] is True
    assert packet["summary"]["all_dispatch_and_reputation_blocked"] is True
    for source in packet["source_decisions"]:
        assert source["review_decision"] == "hold_not_approved_not_publishable"
        assert source["customer_delivery_approval"] is False
        assert source["publication_approved"] is False
        assert source["promotion_allowed"] is False


def test_review_rows_are_packaging_pricing_workflow_only():
    packet = build_aas_three_family_packaging_review_packet()

    expected_families = {spec["family_id"] for spec in SOURCE_DECISION_SPECS}
    assert {row["family_id"] for row in packet["review_rows"]} == expected_families
    for row in packet["review_rows"]:
        assert row["current_ladder_step"] == "explicit_internal_admin_sample_output_hold_decision"
        assert row["packaging_state"] == "internal_admin_package_candidate_only"
        assert row["pricing_state"] == "pricing_inputs_reviewable_but_no_public_price_or_quote_approved"
        assert row["operator_workflow_state"] == "queue_and_review_steps_discussable_but_not_launch_ready"
        assert "separate human-operator approval artifact" in row["next_smallest_gate"]
        assert all(value is False for value in row["readiness"].values())


def test_packet_keeps_all_external_readiness_flags_false_and_claims_blocked():
    packet = build_aas_three_family_packaging_review_packet()

    for flag in READINESS_FALSE_FLAGS:
        assert packet["readiness"][flag] is False
    for claim in PACKET_BLOCKED_CLAIMS:
        assert claim in packet["do_not_claim_yet"]
        assert claim not in packet["safe_to_claim"]
    assert "publish customer copy" in packet["packaging_review_boundaries"]["forbidden"]
    assert "mount catalog or public routes" in packet["packaging_review_boundaries"]["forbidden"]
    assert "dispatch workers from this packet" in packet["packaging_review_boundaries"]["forbidden"]
    assert "attach ERC-8004 reputation receipts" in packet["packaging_review_boundaries"]["forbidden"]
    assert "release exact GPS/raw metadata" in packet["packaging_review_boundaries"]["forbidden"]


def test_write_packaging_review_packet_persists_valid_artifact(tmp_path):
    path = write_aas_three_family_packaging_review_packet(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME
    assert load_aas_three_family_packaging_review_packet(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_customer_delivery_flip_fails_closed():
    sources = source_decisions()
    sources["incident_verification"] = copy.deepcopy(sources["incident_verification"])
    sources["incident_verification"]["customer_delivery_approval"] = True

    with pytest.raises(CityOpsContractError, match="source promoted readiness"):
        build_aas_three_family_packaging_review_packet(source_decisions=sources)


def test_source_ladder_promotion_fails_closed():
    sources = source_decisions()
    sources["document_handoff"] = copy.deepcopy(sources["document_handoff"])
    sources["document_handoff"]["ladder_boundary"]["promotion_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source promoted ladder boundary"):
        build_aas_three_family_packaging_review_packet(source_decisions=sources)


def test_loader_fails_closed_on_packet_readiness_flip(tmp_path):
    packet = build_aas_three_family_packaging_review_packet()
    packet["readiness"]["public_route_ready"] = True
    (tmp_path / AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_aas_three_family_packaging_review_packet(artifact_dir=tmp_path)


def test_loader_fails_closed_on_row_readiness_flip(tmp_path):
    packet = build_aas_three_family_packaging_review_packet()
    packet["review_rows"][0]["readiness"]["customer_delivery_ready"] = True
    (tmp_path / AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="row promoted readiness"):
        load_aas_three_family_packaging_review_packet(artifact_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    packet = build_aas_three_family_packaging_review_packet()
    packet["safe_to_claim"].append("customer_delivery_approved")
    (tmp_path / AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_aas_three_family_packaging_review_packet(artifact_dir=tmp_path)
