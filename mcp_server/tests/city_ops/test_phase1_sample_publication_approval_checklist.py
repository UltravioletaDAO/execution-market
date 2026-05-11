import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.phase1_operator_reviewed_sample_outputs import (
    PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME,
    PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SAFE_CLAIM,
    build_phase1_operator_reviewed_sample_outputs,
)
from mcp_server.city_ops.phase1_sample_publication_approval_checklist import (
    CHECKLIST_GATE_ORDER,
    PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME,
    PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SAFE_CLAIM,
    PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SCHEMA,
    build_phase1_sample_publication_approval_checklist,
    load_phase1_sample_publication_approval_checklist,
    write_phase1_sample_publication_approval_checklist,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
REVIEWED_FIXTURE_DIR = FIXTURES / "phase1_offer_fixture_specs" / "reviewed_outputs"


def read_packet() -> dict:
    with (
        REVIEWED_FIXTURE_DIR / PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME
    ).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def seed_sample_outputs(tmp_path: Path) -> None:
    packet = build_phase1_operator_reviewed_sample_outputs()
    (tmp_path / PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )


def test_sample_publication_checklist_matches_persisted_artifact():
    packet = build_phase1_sample_publication_approval_checklist()

    assert packet == read_packet()
    assert load_phase1_sample_publication_approval_checklist() == packet
    assert packet["schema"] == PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SCHEMA
    assert packet["scope"] == "internal_admin_publication_approval_checklist_only"
    assert PHASE1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_SAFE_CLAIM in packet["safe_to_claim"]
    assert PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_SAFE_CLAIM in packet[
        "safe_to_claim"
    ]


def test_checklist_is_not_publication_approval_or_customer_copy():
    packet = build_phase1_sample_publication_approval_checklist()

    assert packet["publication_approval_status"] == "not_approved_internal_checklist_only"
    assert packet["customer_copy_created"] is False
    assert packet["customer_copy_ready"] is False
    assert packet["customer_visible_catalog_ready"] is False
    assert packet["public_service_catalog_ready"] is False
    assert packet["customer_pilot_exposure_allowed"] is False
    assert packet["front_door_sku_ready"] is False
    assert packet["sample_outputs_publishable"] is False
    assert packet["publication_approved"] is False
    assert packet["publish_route_ready"] is False
    assert packet["live_acontext_ready"] is False
    assert packet["runtime_parity_proven"] is False
    assert packet["autonomous_dispatch_ready"] is False
    assert packet["reputation_ready"] is False
    assert packet["worker_skill_dna_ready"] is False
    assert packet["worker_copyable_doctrine_ready"] is False
    assert packet["exact_gps_or_raw_metadata_exposure_allowed"] is False


def test_required_gates_keep_approval_steps_false():
    packet = build_phase1_sample_publication_approval_checklist()

    assert packet["approval_gates_required"] == CHECKLIST_GATE_ORDER
    assert list(packet["approval_gates_status"].keys()) == CHECKLIST_GATE_ORDER
    assert packet["approval_gates_status"]["source_sample_packet_validated"]["verified"] is True
    assert packet["approval_gates_status"]["safe_and_blocked_claims_travel_together"][
        "verified"
    ] is True
    assert packet["approval_gates_status"]["evidence_redaction_review_required"][
        "verified"
    ] is False
    assert packet["approval_gates_status"]["operator_publish_approval_required"][
        "verified"
    ] is False
    assert packet["approval_gates_status"]["customer_delivery_approval_required"][
        "verified"
    ] is False
    for status in packet["approval_gates_status"].values():
        assert status["approval_granted"] is False


def test_offer_publication_reviews_are_not_publishable():
    packet = build_phase1_sample_publication_approval_checklist()

    assert packet["offer_order"] == [
        "counter_reality_check",
        "packet_submission_attempt",
        "posting_compliance_check",
    ]
    reviews = {review["offer"]: review for review in packet["offer_publication_reviews"]}
    assert set(reviews) == set(packet["offer_order"])
    for review in reviews.values():
        assert review["publication_ready"] is False
        assert review["sample_publishable"] is False
        assert review["customer_copy_ready"] is False
        assert review["operator_publish_approval"] is False
        assert review["customer_delivery_approval"] is False
        assert "operator publish approval" in review["required_before_publication"]
        assert "customer delivery approval" in review["required_before_publication"]
        assert "blocked-claim adjacency check" in review["required_before_publication"]


def test_claim_boundaries_stay_adjacent_and_conservative():
    packet = build_phase1_sample_publication_approval_checklist()
    key_order = list(packet.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert not set(packet["safe_to_claim"]) & set(packet["do_not_claim_yet"])
    assert "publication_approval_ready" in packet["do_not_claim_yet"]
    assert "sample_output_publication_ready" in packet["do_not_claim_yet"]
    assert "customer_copy_ready" in packet["do_not_claim_yet"]
    assert "public_service_catalog_ready" in packet["do_not_claim_yet"]
    assert "erc8004_reputation_ready" in packet["do_not_claim_yet"]
    assert "exact_gps_or_raw_metadata_exposure_allowed" in packet["do_not_claim_yet"]


def test_write_sample_publication_checklist_persists_valid_artifact(tmp_path):
    seed_sample_outputs(tmp_path)

    path = write_phase1_sample_publication_approval_checklist(fixture_dir=tmp_path)

    assert path == tmp_path / PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME
    assert load_phase1_sample_publication_approval_checklist(fixture_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_source_sample_outputs_publishable_flip_fails_closed():
    source = build_phase1_operator_reviewed_sample_outputs()
    source["sample_outputs_publishable"] = True

    with pytest.raises(CityOpsContractError, match="source promoted readiness"):
        build_phase1_sample_publication_approval_checklist(sample_outputs=source)


def test_source_sample_publish_approval_flip_fails_closed():
    source = build_phase1_operator_reviewed_sample_outputs()
    source["offer_sample_outputs"][0]["separate_reviews"][
        "operator_publish_approval"
    ] = True

    with pytest.raises(CityOpsContractError, match="source publish approval drift"):
        build_phase1_sample_publication_approval_checklist(sample_outputs=source)


def test_loader_fails_closed_on_publication_approved_flip(tmp_path):
    packet = build_phase1_sample_publication_approval_checklist()
    packet["publication_approved"] = True
    (tmp_path / PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_phase1_sample_publication_approval_checklist(fixture_dir=tmp_path)


def test_loader_fails_closed_on_forbidden_safe_claim(tmp_path):
    packet = build_phase1_sample_publication_approval_checklist()
    packet["safe_to_claim"].append("publication_approval_ready")
    (tmp_path / PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        load_phase1_sample_publication_approval_checklist(fixture_dir=tmp_path)


def test_loader_fails_closed_on_offer_publishability_flip(tmp_path):
    packet = build_phase1_sample_publication_approval_checklist()
    packet["offer_publication_reviews"][1]["sample_publishable"] = True
    (tmp_path / PHASE1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_FILENAME).write_text(
        json.dumps(packet), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="offer review promoted readiness"):
        load_phase1_sample_publication_approval_checklist(fixture_dir=tmp_path)


def test_source_missing_blocked_claim_fails_closed():
    source = copy.deepcopy(build_phase1_operator_reviewed_sample_outputs())
    source["do_not_claim_yet"] = [
        claim
        for claim in source["do_not_claim_yet"]
        if claim != "customer_copy_ready"
    ]

    with pytest.raises(CityOpsContractError, match="source missing blocked claims"):
        build_phase1_sample_publication_approval_checklist(sample_outputs=source)
