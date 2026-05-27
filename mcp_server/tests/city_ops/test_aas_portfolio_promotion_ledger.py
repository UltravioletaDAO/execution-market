import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_portfolio_promotion_ledger import (
    AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME,
    AAS_PORTFOLIO_PROMOTION_LEDGER_SAFE_CLAIM,
    AAS_PORTFOLIO_PROMOTION_LEDGER_SCHEMA,
    FAMILY_ORDER,
    LEDGER_BLOCKED_CLAIMS,
    LEDGER_FALSE_FLAGS,
    SUMMARY_COUNTERS_ZERO,
    build_aas_portfolio_promotion_ledger,
    load_aas_portfolio_promotion_ledger,
    write_aas_portfolio_promotion_ledger,
)
from mcp_server.city_ops.aas_single_boundary_human_operator_approval_record import (
    AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM,
    build_aas_single_boundary_human_operator_approval_record,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.document_handoff_sample_output_review_decision import (
    DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    build_document_handoff_sample_output_review_decision,
)
from mcp_server.city_ops.incident_verification_sample_output_review_decision import (
    INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
)
from mcp_server.city_ops.local_data_collection_sample_output_review_decision import (
    LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM,
    build_local_data_collection_sample_output_review_decision,
)
from mcp_server.city_ops.retail_reality_pending_approval_status_card import (
    RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM,
    build_retail_reality_pending_approval_status_card,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
ARTIFACT_DIR = FIXTURES / "aas_package_ladder"


def read_ledger() -> dict:
    with (ARTIFACT_DIR / AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def seed_sources(tmp_path: Path) -> None:
    for source_path in ARTIFACT_DIR.glob("*.json"):
        (tmp_path / source_path.name).write_text(
            source_path.read_text(encoding="utf-8"), encoding="utf-8"
        )


def test_ledger_matches_persisted_artifact_and_loader():
    ledger = build_aas_portfolio_promotion_ledger()

    assert ledger == read_ledger()
    assert load_aas_portfolio_promotion_ledger() == ledger
    assert ledger["schema"] == AAS_PORTFOLIO_PROMOTION_LEDGER_SCHEMA
    assert ledger["scope"] == "internal_admin_aas_portfolio_promotion_ledger_only_no_customer_exposure"
    assert (
        ledger["ledger_status"]
        == "read_only_portfolio_promotion_ledger_all_public_delivery_dispatch_runtime_claims_blocked"
    )
    assert AAS_PORTFOLIO_PROMOTION_LEDGER_SAFE_CLAIM in ledger["safe_to_claim"]


def test_ledger_tracks_five_families_in_expected_order():
    ledger = build_aas_portfolio_promotion_ledger()
    rows = ledger["family_rows"]

    assert [row["family_id"] for row in rows] == FAMILY_ORDER
    assert [row["decision_posture"] for row in rows] == [
        "approved_internal_label_only_no_delivery_path",
        "held_not_approved_not_publishable",
        "held_not_approved_not_publishable",
        "pending_human_review_not_approved",
        "held_not_approved_not_publishable",
    ]
    assert rows[0]["latest_safe_claim"] == AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_SAFE_CLAIM
    assert rows[1]["latest_safe_claim"] == DOCUMENT_HANDOFF_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM
    assert rows[2]["latest_safe_claim"] == INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM
    assert rows[3]["latest_safe_claim"] == RETAIL_REALITY_PENDING_APPROVAL_STATUS_CARD_SAFE_CLAIM
    assert rows[4]["latest_safe_claim"] == LOCAL_DATA_COLLECTION_SAMPLE_OUTPUT_REVIEW_DECISION_SAFE_CLAIM


def test_summary_counts_fail_closed_for_customer_public_dispatch_runtime_and_reputation():
    ledger = build_aas_portfolio_promotion_ledger()
    summary = ledger["ledger_summary"]

    assert summary["families_tracked"] == 5
    assert summary["families_with_internal_label_approval_only"] == 1
    assert summary["families_held"] == 3
    assert summary["families_pending_human_review_not_approved"] == 1
    for key in SUMMARY_COUNTERS_ZERO:
        assert summary[key] == 0
    for flag in LEDGER_FALSE_FLAGS:
        assert ledger[flag] is False


def test_family_rows_keep_all_promotion_flags_false():
    ledger = build_aas_portfolio_promotion_ledger()

    for row in ledger["family_rows"]:
        for flag in [
            "customer_delivery_authorized",
            "publication_authorized",
            "public_or_catalog_route_ready",
            "pricing_or_customer_quote_ready",
            "queue_or_dispatch_ready",
            "reputation_attachment_ready",
            "live_acontext_runtime_parity",
            "exact_gps_or_raw_metadata_release_allowed",
            "worker_copyable_doctrine_ready",
        ]:
            assert row[flag] is False
        assert row["family_specific_blocked_claims"]


def test_claim_boundaries_keep_safe_and_blocked_adjacent():
    ledger = build_aas_portfolio_promotion_ledger()
    key_order = list(ledger.keys())

    assert key_order.index("do_not_claim_yet") == key_order.index("safe_to_claim") + 1
    assert AAS_PORTFOLIO_PROMOTION_LEDGER_SAFE_CLAIM in ledger["safe_to_claim"]
    assert not set(ledger["safe_to_claim"]) & set(ledger["do_not_claim_yet"])
    assert ledger["still_blocked_claims"] == ledger["do_not_claim_yet"]
    for claim in LEDGER_BLOCKED_CLAIMS:
        assert claim in ledger["do_not_claim_yet"]
        assert claim not in ledger["safe_to_claim"]
    for forbidden in [
        "customer_delivery_approved",
        "publication_approved",
        "public_catalog_ready",
        "dispatch_ready",
        "erc8004_reputation_ready",
        "live_acontext_ready",
        "worker_copyable_doctrine_ready",
    ]:
        assert forbidden not in ledger["safe_to_claim"]


def test_source_digests_are_recorded_for_parity_review():
    ledger = build_aas_portfolio_promotion_ledger()
    sources = ledger["source_artifacts"]

    assert set(sources) == {
        "compliance_desk",
        "document_handoff",
        "incident_verification",
        "retail_reality",
        "local_data_collection",
    }
    for source in sources.values():
        assert len(source["digest_sha256"]) == 64
        assert source["safe_claim"] in ledger["safe_to_claim"]


def test_write_ledger_persists_valid_artifact(tmp_path):
    seed_sources(tmp_path)

    path = write_aas_portfolio_promotion_ledger(artifact_dir=tmp_path)

    assert path == tmp_path / AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME
    assert load_aas_portfolio_promotion_ledger(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )


def test_compliance_customer_delivery_promotion_fails_closed():
    compliance = build_aas_single_boundary_human_operator_approval_record()
    compliance = copy.deepcopy(compliance)
    compliance["customer_delivery_approved"] = True

    with pytest.raises(CityOpsContractError, match="compliance source promoted customer_delivery_approved"):
        build_aas_portfolio_promotion_ledger(compliance_record=compliance)


def test_document_forbidden_safe_claim_fails_closed():
    document = build_document_handoff_sample_output_review_decision()
    document = copy.deepcopy(document)
    document["safe_to_claim"].append("customer_delivery_approved")

    with pytest.raises(CityOpsContractError, match="document source forbidden safe claims"):
        build_aas_portfolio_promotion_ledger(document_decision=document)


def test_retail_approval_promotion_fails_closed():
    retail = build_retail_reality_pending_approval_status_card()
    retail = copy.deepcopy(retail)
    retail["human_operator_approval_recorded"] = True

    with pytest.raises(CityOpsContractError, match="retail source approval promoted"):
        build_aas_portfolio_promotion_ledger(retail_status_card=retail)


def test_local_data_runtime_promotion_fails_closed():
    local_data = build_local_data_collection_sample_output_review_decision()
    local_data = copy.deepcopy(local_data)
    local_data["readiness"]["live_acontext_ready"] = True

    with pytest.raises(CityOpsContractError, match="local data source promoted readiness.live_acontext_ready"):
        build_aas_portfolio_promotion_ledger(local_data_decision=local_data)


def test_loader_fails_closed_on_summary_promotion(tmp_path):
    seed_sources(tmp_path)
    ledger = build_aas_portfolio_promotion_ledger(artifact_dir=tmp_path)
    ledger["ledger_summary"]["families_ready_for_queue_or_dispatch"] = 1
    (tmp_path / AAS_PORTFOLIO_PROMOTION_LEDGER_FILENAME).write_text(
        json.dumps(ledger), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted summary families_ready_for_queue_or_dispatch"):
        load_aas_portfolio_promotion_ledger(artifact_dir=tmp_path)
