import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_live_preflight import (
    build_acontext_live_preflight_result,
    build_blocked_acontext_preflight_probe,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.coordination_intelligence import (
    build_coordination_intelligence_snapshot,
)
from mcp_server.city_ops.decision_support_matrix_card import (
    DECISION_SUPPORT_MATRIX_CARD_FILENAME,
    DECISION_SUPPORT_MATRIX_CARD_SAFE_CLAIM,
    DECISION_SUPPORT_MATRIX_CARD_SCHEMA,
    build_decision_support_matrix_card,
    load_decision_support_matrix_card,
    write_decision_support_matrix_card_fixture,
)
from mcp_server.city_ops.decision_support_readiness_matrix import (
    DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
    build_decision_support_readiness_matrix,
)
from mcp_server.city_ops.operator_debug_surface import build_operator_debug_surface
from mcp_server.city_ops.proof_observability import build_proof_observability_snapshot

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_card() -> dict:
    with (PROOF_BLOCK_DIR / DECISION_SUPPORT_MATRIX_CARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_decision_support_matrix_card_consumes_matrix_only():
    card = build_decision_support_matrix_card()

    assert card["schema"] == DECISION_SUPPORT_MATRIX_CARD_SCHEMA
    assert card["derived_from"]["read_only"] is True
    assert card["derived_from"]["source_artifacts"] == [
        DECISION_SUPPORT_READINESS_MATRIX_FILENAME
    ]
    assert card["derived_from"]["consumes_only"] == [
        DECISION_SUPPORT_READINESS_MATRIX_FILENAME
    ]
    assert card["access_policy"]["audience"] == "internal_admin_only"
    assert card["access_policy"]["requires_admin_context"] is True
    assert card["access_policy"]["public_route_registered"] is False
    assert card["render_contract"]["network_route_registered"] is False
    assert card["render_contract"]["layout"] == "four_axis_matrix_card"
    assert card["render_contract"]["allowed_interpretation"] == (
        "pass_through_matrix_fields_only"
    )
    assert DECISION_SUPPORT_MATRIX_CARD_SAFE_CLAIM in card["claim_boundaries"][
        "safe_to_claim"
    ]


def test_decision_support_matrix_card_preserves_four_axis_matrix_fields():
    matrix = build_decision_support_readiness_matrix()
    card = build_decision_support_matrix_card(matrix=matrix)

    axes = {axis["axis"]: axis for axis in matrix["handoff_axes"]}
    rendered = {axis["card"]: axis for axis in card["axis_cards"]}

    assert set(rendered) == {
        "memory_system_to_acontext_bridge",
        "irc_session_management",
        "cross_project_decision_support",
        "agent_observability_success_metrics",
    }
    assert set(rendered) == set(axes)
    for axis_name, source in axes.items():
        row = rendered[axis_name]
        assert row["state"] == source["state"]
        assert row["ready_now"] == source["ready_now"]
        assert row["safe_use"] == source["safe_use"]
        assert row["blocked_until"] == source["blocked_until"]
        assert row["evidence"] == source["evidence"]

    assert rendered["memory_system_to_acontext_bridge"]["ready_now"] is False
    assert rendered["irc_session_management"]["display_status"] == (
        "ready_for_operator_planning"
    )
    assert card["success_metrics"] == matrix["success_metrics"]
    assert card["recommended_next_action"] == matrix["recommended_next_action"]


def test_decision_support_matrix_card_matches_persisted_fixture():
    card = build_decision_support_matrix_card()

    assert card == read_fixture_card()
    assert load_decision_support_matrix_card() == card


def test_decision_support_matrix_card_keeps_safe_and_blocked_claim_cards_adjacent():
    card = build_decision_support_matrix_card()
    cards = {claim_card["card"]: claim_card for claim_card in card["claim_cards"]}

    assert cards["safe_to_claim"]["status"] == "visible_without_softening"
    assert DECISION_SUPPORT_MATRIX_CARD_SAFE_CLAIM in cards["safe_to_claim"]["values"]
    assert cards["do_not_claim_yet"]["status"] == "visible_without_softening"
    assert "acontext_sink_ready" in cards["do_not_claim_yet"]["values"]
    assert "worker_copyable_municipal_doctrine" in cards["do_not_claim_yet"]["values"]
    assert not set(cards["safe_to_claim"]["values"]) & set(
        cards["do_not_claim_yet"]["values"]
    )


def test_decision_support_matrix_card_blocks_external_or_product_claims():
    card = build_decision_support_matrix_card()
    blocked = set(card["claim_boundaries"]["do_not_claim_yet"])

    assert "public_route_ready" in blocked
    assert "customer_visible_catalog_ready" in blocked
    assert "customer_copy_ready" in blocked
    assert "dispatch_automation_ready" in blocked
    assert "live_acontext_readiness" in blocked
    assert "acontext_sink_ready" in blocked
    assert "runtime_parity_proven" in blocked
    assert "erc8004_reputation_ready" in blocked
    assert "worker_skill_dna_ready" in blocked
    assert "legal_sufficiency" in blocked
    assert "regulator_acceptance" in blocked
    assert "exact_gps_or_metadata_exposure" in blocked

    readiness = card["readiness"]
    assert readiness["matrix_card_landed"] is True
    for key, value in readiness.items():
        if key in {"matrix_card_landed", "source_ready_to_attempt_live_transport"}:
            continue
        assert value is False


def test_decision_support_matrix_card_can_show_transport_attemptable_without_readiness():
    probe = build_blocked_acontext_preflight_probe()
    probe["docker"].update({"available": True, "exit_code": 0, "error": None})
    probe["python_sdk"]["available"] = True
    probe["api"].update({"reachable": True, "status_code": 200, "error": None})
    probe["dashboard"].update({"reachable": True, "status_code": 200, "error": None})
    preflight = build_acontext_live_preflight_result(probe=probe)
    surface = build_operator_debug_surface(acontext_live_preflight_result=preflight)
    observability = build_proof_observability_snapshot(operator_debug_surface=surface)
    coordination = build_coordination_intelligence_snapshot(
        proof_observability_snapshot=observability
    )
    matrix = build_decision_support_readiness_matrix(
        coordination_intelligence_snapshot=coordination
    )

    card = build_decision_support_matrix_card(matrix=matrix)

    assert card["card_verdict"] == (
        "decision_support_matrix_card_landed_live_transport_attemptable_not_ready"
    )
    assert card["readiness"]["source_ready_to_attempt_live_transport"] is True
    assert card["readiness"]["acontext_sink_ready"] is False
    axes = {axis["card"]: axis for axis in card["axis_cards"]}
    assert axes["memory_system_to_acontext_bridge"]["state"] == (
        "attemptable_not_ready"
    )


def test_decision_support_matrix_card_refuses_promoted_matrix_readiness():
    matrix = copy.deepcopy(build_decision_support_readiness_matrix())
    matrix["readiness"]["acontext_sink_ready"] = True

    with pytest.raises(CityOpsContractError, match="promoted matrix readiness"):
        build_decision_support_matrix_card(matrix=matrix)


def test_decision_support_matrix_card_refuses_interpretation_drift(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
        tmp_path / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
    )
    path = write_decision_support_matrix_card_fixture(artifact_dir=tmp_path)
    card = json.loads(path.read_text(encoding="utf-8"))
    card["render_contract"]["allowed_interpretation"] = "summarize_and_rewrite"
    path.write_text(json.dumps(card), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="interpretation drift"):
        load_decision_support_matrix_card(artifact_dir=tmp_path)


def test_write_decision_support_matrix_card_persists_valid_artifact(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
        tmp_path / DECISION_SUPPORT_READINESS_MATRIX_FILENAME,
    )
    path = write_decision_support_matrix_card_fixture(artifact_dir=tmp_path)

    assert path == tmp_path / DECISION_SUPPORT_MATRIX_CARD_FILENAME
    assert load_decision_support_matrix_card(artifact_dir=tmp_path) == json.loads(
        path.read_text(encoding="utf-8")
    )
