import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_approved_offer_customer_delivery_hold_checklist import (
    CUSTOMER_DELIVERY_VERDICT,
    PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_FILENAME,
    PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_SAFE_CLAIM,
    PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_SCHEMA,
    REQUIRED_BLOCKED_CLAIMS,
    REQUIRED_DELIVERY_PREREQUISITES,
    build_phase1_approved_offer_customer_delivery_hold_checklist,
    load_phase1_approved_offer_customer_delivery_hold_checklist,
    write_phase1_approved_offer_customer_delivery_hold_checklist,
)
from mcp_server.city_ops.phase1_customer_facing_draft_packet import (
    PHASE1_CUSTOMER_FACING_DRAFT_PACKET_FILENAME,
    build_phase1_customer_facing_draft_packet,
)
from mcp_server.city_ops.phase1_draft_packet_operator_review_decision import (
    PHASE1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_FILENAME,
    build_phase1_draft_packet_operator_review_decision,
)
from mcp_server.city_ops.phase1_offer_card_approval_coverage_matrix import (
    PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME,
    PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SAFE_CLAIM,
    build_phase1_offer_card_approval_coverage_matrix,
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
    with (
        REVIEWED_FIXTURE_DIR
        / PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    draft = build_phase1_customer_facing_draft_packet()
    decision = build_phase1_draft_packet_operator_review_decision(draft_packet=draft)
    approval = build_phase1_offer_card_human_operator_approval_record(
        draft_packet=draft, review_decision=decision
    )
    matrix = build_phase1_offer_card_approval_coverage_matrix(
        draft_packet=draft, review_decision=decision, approval_record=approval
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
    (tmp_path / PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_FILENAME).write_text(
        json.dumps(matrix), encoding="utf-8"
    )


def test_delivery_hold_checklist_matches_persisted_artifact():
    packet = build_phase1_approved_offer_customer_delivery_hold_checklist()

    assert packet == read_packet()
    assert load_phase1_approved_offer_customer_delivery_hold_checklist() == packet
    assert packet["schema"] == PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_SCHEMA
    assert packet["scope"] == (
        "internal_admin_single_approved_offer_customer_delivery_hold_checklist_only"
    )
    assert PHASE1_OFFER_CARD_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM in packet["safe_to_claim"]
    assert PHASE1_OFFER_CARD_APPROVAL_COVERAGE_MATRIX_SAFE_CLAIM in packet["safe_to_claim"]
    assert PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_SAFE_CLAIM in packet[
        "safe_to_claim"
    ]


def test_delivery_hold_checklist_keeps_single_approved_offer_held():
    packet = build_phase1_approved_offer_customer_delivery_hold_checklist()

    assert packet["delivery_hold_status"] == (
        "text_boundary_approved_customer_delivery_hold_required"
    )
    assert packet["customer_delivery_verdict"] == CUSTOMER_DELIVERY_VERDICT
    assert packet["approved_offer"] == APPROVED_OFFER
    assert packet["coverage_context"] == {
        "text_boundary_approved_offer_count": 1,
        "unapproved_offer_cards": ["packet_submission_attempt", "posting_compliance_check"],
        "coverage_complete": False,
        "customer_delivery_ready": False,
        "operator_publish_ready": False,
        "publication_ready": False,
    }


def test_delivery_prerequisites_are_all_unsatisfied_before_customer_exposure():
    packet = build_phase1_approved_offer_customer_delivery_hold_checklist()
    prerequisites = packet["delivery_prerequisites"]

    assert [item["prerequisite"] for item in prerequisites] == REQUIRED_DELIVERY_PREREQUISITES
    for item in prerequisites:
        assert item["satisfied"] is False
        assert item["required_before_customer_exposure"] is True
        assert item["approval_boundary"] == "delivery_hold_check_only_not_customer_delivery"


def test_redactions_are_carried_forward_but_require_fresh_delivery_reverification():
    packet = build_phase1_approved_offer_customer_delivery_hold_checklist()
    redactions = packet["redaction_checks_carried_forward"]

    assert [item["check"] for item in redactions] == REQUIRED_REDACTION_CHECKS
    for item in redactions:
        assert item["source_passed"] is True
        assert item["fresh_delivery_reverification_required"] is True
        assert item["customer_delivery_allowed"] is False


def test_publication_customer_delivery_dispatch_reputation_and_metadata_stay_blocked():
    packet = build_phase1_approved_offer_customer_delivery_hold_checklist()

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


def test_delivery_path_and_channels_remain_internal_only():
    packet = build_phase1_approved_offer_customer_delivery_hold_checklist()

    assert packet["authorized_delivery_path_boundary"] == {
        "approved_record_path": AUTHORIZED_DELIVERY_PATH,
        "customer_delivery_allowed": False,
        "public_route_allowed": False,
        "catalog_route_allowed": False,
        "dispatch_allowed": False,
        "reputation_attachment_allowed": False,
        "exact_gps_or_raw_metadata_allowed": False,
    }
    assert packet["delivery_channel_hold"] == {
        "internal_admin_operator_queue_only": True,
        "customer_email_allowed": False,
        "customer_dashboard_allowed": False,
        "public_catalog_allowed": False,
        "api_route_allowed": False,
        "worker_visible_instruction_allowed": False,
    }


def test_claim_boundaries_stay_adjacent_and_conservative():
    packet = build_phase1_approved_offer_customer_delivery_hold_checklist()
    key_order = list(packet.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert not set(packet["safe_to_claim"]) & set(packet["do_not_claim_yet"])
    assert "customer_delivery_ready" not in packet["safe_to_claim"]
    assert "customer_delivery_approved" not in packet["safe_to_claim"]
    assert "publication_approved" not in packet["safe_to_claim"]
    assert "phase1_approval_coverage_complete" not in packet["safe_to_claim"]


def test_write_delivery_hold_checklist_persists_valid_artifact(tmp_path):
    seed_sources(tmp_path)

    path = write_phase1_approved_offer_customer_delivery_hold_checklist(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_FILENAME
    assert load_phase1_approved_offer_customer_delivery_hold_checklist(
        fixture_dir=tmp_path
    ) == json.loads(path.read_text(encoding="utf-8"))


def test_source_coverage_customer_delivery_flip_fails_closed():
    matrix = build_phase1_offer_card_approval_coverage_matrix()
    approval = build_phase1_offer_card_human_operator_approval_record()
    matrix["approval_summary"]["customer_delivery_ready"] = True

    with pytest.raises(CityOpsContractError, match="source coverage promoted summary readiness"):
        build_phase1_approved_offer_customer_delivery_hold_checklist(
            coverage_matrix=matrix, approval_record=approval
        )


def test_source_approval_offer_drift_fails_closed():
    matrix = build_phase1_offer_card_approval_coverage_matrix()
    approval = build_phase1_offer_card_human_operator_approval_record()
    approval["approved_offer"] = "packet_submission_attempt"

    with pytest.raises(CityOpsContractError, match="source approval offer drift"):
        build_phase1_approved_offer_customer_delivery_hold_checklist(
            coverage_matrix=matrix, approval_record=approval
        )


def test_loader_fails_closed_on_customer_delivery_verdict_promotion(tmp_path):
    packet = build_phase1_approved_offer_customer_delivery_hold_checklist()
    packet["customer_delivery_verdict"] = "ready_for_customer_delivery"
    (tmp_path / PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="verdict drift"):
        load_phase1_approved_offer_customer_delivery_hold_checklist(fixture_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    packet = build_phase1_approved_offer_customer_delivery_hold_checklist()
    packet = copy.deepcopy(packet)
    packet["safe_to_claim"].append("customer_delivery_ready")
    (tmp_path / PHASE1_APPROVED_OFFER_CUSTOMER_DELIVERY_HOLD_CHECKLIST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_phase1_approved_offer_customer_delivery_hold_checklist(fixture_dir=tmp_path)
