from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.decision_support_matrix_card import (
    DECISION_SUPPORT_MATRIX_CARD_FILENAME,
)
from mcp_server.city_ops.decision_support_matrix_operator_consumer import (
    DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME,
    DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SAFE_CLAIM,
    build_decision_support_matrix_operator_consumer,
)
from mcp_server.city_ops.decision_support_matrix_operator_display_adapter import (
    DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME,
    DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SAFE_CLAIM,
    DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SCHEMA,
    build_decision_support_matrix_operator_display_adapter,
    load_decision_support_matrix_operator_display_adapter,
    write_decision_support_matrix_operator_display_adapter_fixture,
)
from mcp_server.city_ops.decision_support_readiness_matrix import (
    DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def copy_required_artifacts(tmp_path: Path) -> None:
    for filename in [
        DECISION_SUPPORT_MATRIX_CARD_FILENAME,
        DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
        DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME,
    ]:
        shutil.copy(PROOF_BLOCK_DIR / filename, tmp_path / filename)


def test_operator_display_adapter_matches_persisted_fixture():
    adapter = build_decision_support_matrix_operator_display_adapter()
    loaded = load_decision_support_matrix_operator_display_adapter()

    assert adapter == loaded
    assert adapter["schema"] == DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SCHEMA
    assert adapter["adapter_verdict"] == (
        "operator_display_adapter_landed_internal_admin_data_only_not_ui"
    )
    assert DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_SAFE_CLAIM in adapter[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_SAFE_CLAIM in adapter[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_operator_display_adapter_consumes_only_consumer_artifact():
    adapter = build_decision_support_matrix_operator_display_adapter()

    assert adapter["derived_from"]["consumes_only"] == [
        DECISION_SUPPORT_MATRIX_OPERATOR_CONSUMER_FILENAME
    ]
    assert adapter["derived_from"]["semantic_reinterpretation_performed"] is False
    assert adapter["access_policy"]["audience"] == "internal_admin_only"
    assert adapter["access_policy"]["public_route_registered"] is False
    assert adapter["display_contract"]["network_route_registered"] is False
    assert adapter["display_contract"]["operator_ui_ready"] is False


def test_operator_display_adapter_keeps_safe_and_blocked_claim_cards_adjacent():
    adapter = build_decision_support_matrix_operator_display_adapter()
    cards = {card["card"]: card for card in adapter["display_cards"]}

    assert [card["card"] for card in adapter["display_cards"]][2:4] == [
        "safe_to_claim",
        "do_not_claim_yet",
    ]
    assert cards["safe_to_claim"]["status"] == "visible_without_softening"
    assert cards["do_not_claim_yet"]["status"] == "visible_without_softening"
    assert not (
        set(adapter["claim_boundaries"]["safe_to_claim"])
        & set(adapter["claim_boundaries"]["do_not_claim_yet"])
    )
    assert "acontext_sink_ready" in adapter["claim_boundaries"]["do_not_claim_yet"]
    assert "worker_copyable_municipal_doctrine" in adapter["claim_boundaries"][
        "do_not_claim_yet"
    ]


def test_operator_display_adapter_passes_through_consumer_sections():
    consumer = build_decision_support_matrix_operator_consumer()
    adapter = build_decision_support_matrix_operator_display_adapter(
        operator_consumer=consumer
    )
    cards = {card["card"]: card for card in adapter["display_cards"]}

    assert cards["axis_cards"]["values"] == consumer["operator_consumer_sections"][
        "axis_cards"
    ]
    assert cards["success_metrics"]["values"] == consumer[
        "operator_consumer_sections"
    ]["success_metrics"]
    assert cards["readiness"]["values"] == consumer["operator_consumer_sections"][
        "readiness"
    ]
    assert adapter["display_lines"][0] == (
        f"matrix_verdict: {consumer['operator_consumer_sections']['matrix_verdict']}"
    )


def test_operator_display_adapter_refuses_external_readiness_flags():
    adapter = build_decision_support_matrix_operator_display_adapter()

    for flag in [
        "operator_ui_ready",
        "polished_operator_console_ready",
        "public_route_ready",
        "customer_visible_catalog_ready",
        "dispatch_automation_ready",
        "live_acontext_ready",
        "erc8004_reputation_ready",
        "worker_skill_dna_ready",
        "gps_or_metadata_exposure_allowed",
        "worker_copyable_municipal_doctrine_ready",
    ]:
        assert adapter["readiness"][flag] is False

    for flag in [
        "network_route_registered",
        "public_route_registered",
        "customer_visible",
        "dispatch_enabled",
        "writes_live_acontext",
        "emits_reputation_receipts",
        "exposes_gps_or_metadata",
    ]:
        assert adapter["access_policy"][flag] is False


def test_write_and_load_operator_display_adapter_fixture(tmp_path):
    copy_required_artifacts(tmp_path)

    path = write_decision_support_matrix_operator_display_adapter_fixture(
        artifact_dir=tmp_path
    )
    loaded = load_decision_support_matrix_operator_display_adapter(artifact_dir=tmp_path)

    assert path == tmp_path / DECISION_SUPPORT_MATRIX_OPERATOR_DISPLAY_ADAPTER_FILENAME
    assert loaded == json.loads(path.read_text(encoding="utf-8"))
    assert loaded["readiness"]["display_adapter_landed"] is True


def test_operator_display_adapter_refuses_consumer_access_drift():
    consumer = copy.deepcopy(build_decision_support_matrix_operator_consumer())
    consumer["access_policy"]["customer_visible"] = True

    with pytest.raises(CityOpsContractError, match="consumer access drift"):
        build_decision_support_matrix_operator_display_adapter(operator_consumer=consumer)


def test_operator_display_adapter_loader_refuses_stale_digest(tmp_path):
    copy_required_artifacts(tmp_path)
    path = write_decision_support_matrix_operator_display_adapter_fixture(
        artifact_dir=tmp_path
    )
    adapter = json.loads(path.read_text(encoding="utf-8"))
    adapter["derived_from"]["source_consumer_digest"] = "stale"
    path.write_text(json.dumps(adapter), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="source consumer digest drift"):
        load_decision_support_matrix_operator_display_adapter(artifact_dir=tmp_path)


def test_operator_display_adapter_loader_refuses_card_drift(tmp_path):
    copy_required_artifacts(tmp_path)
    path = write_decision_support_matrix_operator_display_adapter_fixture(
        artifact_dir=tmp_path
    )
    adapter = json.loads(path.read_text(encoding="utf-8"))
    adapter["display_cards"][1]["values"] = []
    path.write_text(json.dumps(adapter), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="axis card drift"):
        load_decision_support_matrix_operator_display_adapter(artifact_dir=tmp_path)


def test_operator_display_adapter_loader_refuses_readiness_promotion(tmp_path):
    copy_required_artifacts(tmp_path)
    path = write_decision_support_matrix_operator_display_adapter_fixture(
        artifact_dir=tmp_path
    )
    adapter = json.loads(path.read_text(encoding="utf-8"))
    adapter["readiness"]["operator_ui_ready"] = True
    path.write_text(json.dumps(adapter), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promotion"):
        load_decision_support_matrix_operator_display_adapter(artifact_dir=tmp_path)
