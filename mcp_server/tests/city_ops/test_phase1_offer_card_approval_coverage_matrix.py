import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_customer_facing_draft_packet import (
    PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME,
    PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM,
    build_phase1_customer_facing_draft_packet,
)
from mcp_server.city_ops.phase1_draft_packet_operator_review_decision import (
    PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME,
    PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM,
    build_phase1_draft_packet_operator_review_decision,
)
from mcp_server.city_ops.phase1_offer_card_approval_coverage_matrix import (
    PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME,
    PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SAFE_CLAIM,
    PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SCHEMA,
    REQUIRED_BLOCKED_CLAIMS,
    build_phase1_offer_card_approval_coverage_matrix,
    load_phase1_offer_card_approval_coverage_matrix,
    write_phase1_offer_card_approval_coverage_matrix,
)
from mcp_server.city_ops.phase1_offer_card_human_operator_approval_record import (
    APPROVED_OFFER,
    AUTHORIZED_DELIVERY_PATH,
    PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME,
    PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
    REQUIRED_REDACTION_CHECKS,
    build_phase1_offer_card_human_operator_approval_record,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_packet() -> dict:
    with (REVIEWED_FIXTURE_DIR / PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    draft = build_phase1_customer_facing_draft_packet()
    decision = build_phase1_draft_packet_operator_review_decision(draft_packet=draft)
    approval = build_phase1_offer_card_human_operator_approval_record(
        draft_packet=draft, review_decision=decision
    )
    (tmp_path / PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME).write_text(
        json.dumps(draft), encoding="utf-8"
    )
    (tmp_path / PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME).write_text(
        json.dumps(decision), encoding="utf-8"
    )
    (tmp_path / PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_FILENAME).write_text(
        json.dumps(approval), encoding="utf-8"
    )


def test_offer_card_approval_coverage_matrix_matches_persisted_artifact():
    packet = build_phase1_offer_card_approval_coverage_matrix()

    assert packet == read_packet()
    assert load_phase1_offer_card_approval_coverage_matrix() == packet
    assert packet["schema"] == PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SCHEMA
    assert packet["scope"] == "internal_admin_phase1_offer_card_approval_coverage_matrix_only"
    assert PHASE1_CUSTOMER_FACING_DRAFT_PACKET_SAFE_CLAIM in packet["safe_to_claim"]
    assert PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_SAFE_CLAIM in packet["safe_to_claim"]
    assert PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM in packet["safe_to_claim"]
    assert PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SAFE_CLAIM in packet["safe_to_claim"]


def test_matrix_summarizes_one_approved_and_two_unapproved_offer_cards():
    packet = build_phase1_offer_card_approval_coverage_matrix()
    summary = packet["approval_summary"]

    assert packet["approval_coverage_status"] == (
        "one_offer_text_boundary_approved_two_offer_cards_unapproved_"
        "all_customer_delivery_blocked"
    )
    assert summary["approved_offer_count"] == 1
    assert summary["approved_offers"] == [APPROVED_OFFER]
    assert summary["unapproved_offers"] == [
        "packet_submission_attempt",
        "posting_compliance_check",
    ]
    assert summary["coverage_complete"] is False
    assert summary["customer_delivery_ready"] is False
    assert summary["operator_publish_ready"] is False
    assert summary["publication_ready"] is False


def test_coverage_rows_preserve_approval_boundaries_and_missing_approvals():
    packet = build_phase1_offer_card_approval_coverage_matrix()
    rows = {row["offer"]: row for row in packet["coverage_rows"]}

    approved = rows[APPROVED_OFFER]
    assert approved["human_operator_text_boundary_approved"] is True
    assert approved["approved_delivery_path"] == AUTHORIZED_DELIVERY_PATH
    assert approved["redaction_checks_recorded"] == REQUIRED_REDACTION_CHECKS
    assert approved["row_verdict"] == "text_boundary_approved_but_customer_delivery_still_blocked"
    assert "customer_delivery_approval" in approved["missing_approvals_before_customer_exposure"]
    assert "human_operator_text_boundary_approval" not in approved[
        "missing_approvals_before_customer_exposure"
    ]

    for offer in ["packet_submission_attempt", "posting_compliance_check"]:
        row = rows[offer]
        assert row["human_operator_text_boundary_approved"] is False
        assert row["approved_text_fields"] == []
        assert row["approved_delivery_path"] is None
        assert row["redaction_checks_recorded"] == []
        assert row["row_verdict"] == "missing_human_operator_text_boundary_approval"
        assert "human_operator_text_boundary_approval" in row[
            "missing_approvals_before_customer_exposure"
        ]
        assert "offer_specific_redaction_review_record" in row[
            "missing_approvals_before_customer_exposure"
        ]
        assert "customer_delivery_approval" in row["missing_approvals_before_customer_exposure"]


def test_publication_customer_delivery_dispatch_reputation_and_metadata_stay_blocked():
    packet = build_phase1_offer_card_approval_coverage_matrix()

    for flag in [
        "operator_publish_approval",
        "customer_delivery_approval",
        "customer_copy_created",
        "customer_copy_ready",
        "customer_visible_catalog_ready",
        "public_service_catalog_ready",
        "controlled_concierge_pilot_ready",
        "customer_pilot_exposure_allowed",
        "front_door_sku_ready",
        "draft_packet_publishable",
        "draft_packet_publication_ready",
        "sample_outputs_publishable",
        "publication_approved",
        "publish_route_ready",
        "catalog_route_ready",
        "controlled_pilot_authorized",
        "live_acontext_ready",
        "runtime_parity_proven",
        "autonomous_dispatch_ready",
        "reputation_ready",
        "worker_skill_dna_ready",
        "worker_copyable_doctrine_ready",
        "exact_gps_or_raw_metadata_exposure_allowed",
    ]:
        assert packet[flag] is False

    assert packet["still_blocked_claims"] == packet["do_not_claim_yet"]
    for claim in REQUIRED_BLOCKED_CLAIMS:
        assert claim in packet["still_blocked_claims"]
    assert "phase1_approval_coverage_incomplete" in packet["still_blocked_claims"]
    assert "two_phase1_offer_cards_missing_human_operator_text_boundary_approval" in packet[
        "still_blocked_claims"
    ]


def test_delivery_path_boundary_keeps_external_routes_blocked():
    packet = build_phase1_offer_card_approval_coverage_matrix()

    assert packet["authorized_delivery_path_boundary"] == {
        "approved_record_path": AUTHORIZED_DELIVERY_PATH,
        "customer_delivery_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
    }


def test_claim_boundaries_stay_adjacent_and_conservative():
    packet = build_phase1_offer_card_approval_coverage_matrix()
    key_order = list(packet.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert not set(packet["safe_to_claim"]) & set(packet["do_not_claim_yet"])
    assert "phase1_approval_coverage_complete" not in packet["safe_to_claim"]
    assert "all_offer_cards_approved" not in packet["safe_to_claim"]
    assert "publication_approved" not in packet["safe_to_claim"]
    assert "customer_delivery_approved" not in packet["safe_to_claim"]


def test_write_offer_card_approval_coverage_matrix_persists_valid_artifact(tmp_path):
    seed_sources(tmp_path)

    path = write_phase1_offer_card_approval_coverage_matrix(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME
    assert load_phase1_offer_card_approval_coverage_matrix(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_approval_multiple_offers_fails_closed():
    draft = build_phase1_customer_facing_draft_packet()
    decision = build_phase1_draft_packet_operator_review_decision(draft_packet=draft)
    approval = build_phase1_offer_card_human_operator_approval_record(
        draft_packet=draft, review_decision=decision
    )
    approval["approved_offer_count"] = 2

    with pytest.raises(CityOpsContractError, match="source must approve exactly one offer"):
        build_phase1_offer_card_approval_coverage_matrix(
            draft_packet=draft, review_decision=decision, approval_record=approval
        )


def test_source_approval_delivery_path_flip_fails_closed():
    draft = build_phase1_customer_facing_draft_packet()
    decision = build_phase1_draft_packet_operator_review_decision(draft_packet=draft)
    approval = build_phase1_offer_card_human_operator_approval_record(
        draft_packet=draft, review_decision=decision
    )
    approval["authorized_delivery_path"]["customer_delivery_allowed"] = True

    with pytest.raises(CityOpsContractError, match="source delivery path promoted readiness"):
        build_phase1_offer_card_approval_coverage_matrix(
            draft_packet=draft, review_decision=decision, approval_record=approval
        )


def test_loader_fails_closed_on_unapproved_row_becoming_approved(tmp_path):
    packet = build_phase1_offer_card_approval_coverage_matrix()
    packet["coverage_rows"][1]["human_operator_text_boundary_approved"] = True
    (tmp_path / PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="approved row"):
        load_phase1_offer_card_approval_coverage_matrix(fixture_dir=tmp_path)


def test_loader_fails_closed_on_customer_delivery_flip(tmp_path):
    packet = build_phase1_offer_card_approval_coverage_matrix()
    packet["customer_delivery_approval"] = True
    (tmp_path / PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_phase1_offer_card_approval_coverage_matrix(fixture_dir=tmp_path)


def test_source_draft_card_customer_ready_flip_fails_closed():
    draft = copy.deepcopy(build_phase1_customer_facing_draft_packet())
    decision = build_phase1_draft_packet_operator_review_decision(draft_packet=draft)
    approval = build_phase1_offer_card_human_operator_approval_record(
        draft_packet=draft, review_decision=decision
    )
    draft["draft_cards"][0]["draft_ready_for_customer"] = True

    with pytest.raises(CityOpsContractError, match="source draft card promoted readiness"):
        build_phase1_offer_card_approval_coverage_matrix(
            draft_packet=draft, review_decision=decision, approval_record=approval
        )
