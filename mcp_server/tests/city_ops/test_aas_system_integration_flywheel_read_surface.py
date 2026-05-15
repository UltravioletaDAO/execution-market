import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_system_integration_flywheel import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_SAFE_CLAIM,
    FLYWHEEL_BLOCKED_CLAIMS,
    build_aas_system_integration_flywheel,
)
from mcp_server.city_ops.aas_system_integration_flywheel_read_surface import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SCHEMA,
    SURFACE_BLOCKED_CLAIMS,
    build_aas_system_integration_flywheel_read_surface,
    load_aas_system_integration_flywheel_read_surface,
    write_aas_system_integration_flywheel_read_surface,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_surface() -> dict:
    with (PROOF_BLOCK_DIR / AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_aas_system_integration_flywheel_read_surface_matches_fixture():
    surface = build_aas_system_integration_flywheel_read_surface()

    assert surface == read_fixture_surface()
    assert surface["schema"] == AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SCHEMA
    assert surface["surface_verdict"] == (
        "admin_flywheel_read_surface_landed_live_transport_blocked"
    )
    assert AAS_SYSTEM_INTEGRATION_FLYWHEEL_SAFE_CLAIM in surface["claim_boundaries"][
        "safe_to_claim"
    ]
    assert AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM in surface[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert surface["readiness"]["surface_landed"] is True
    assert surface["readiness"]["surface_promotes_live_readiness"] is False
    assert surface["readiness"]["acontext_sink_ready"] is False
    assert surface["readiness"]["payment_coverage_reverified_by_this_surface"] is False


def test_aas_system_integration_flywheel_read_surface_renders_four_id_header():
    flywheel = build_aas_system_integration_flywheel()
    surface = build_aas_system_integration_flywheel_read_surface(flywheel=flywheel)
    header = surface["four_id_session_header"]

    assert header["proof_anchor_id"] == flywheel["proof_anchor_id"]
    assert header["coordination_session_id"] == flywheel["coordination_session_id"]
    assert header["compact_decision_id"] == flywheel["compact_decision_id"]
    assert header["review_packet_id"] == flywheel["review_packet_id"]
    assert "do not reopen raw transcripts" in header["normal_handoff_rule"]


def test_aas_system_integration_flywheel_read_surface_preserves_cards_and_badges():
    flywheel = build_aas_system_integration_flywheel()
    surface = build_aas_system_integration_flywheel_read_surface(flywheel=flywheel)

    assert len(surface["strength_cards"]) == len(flywheel["declared_strength_inputs"])
    assert len(surface["connection_loop_cards"]) == len(flywheel["connection_loops"])
    assert len(surface["operator_next_action_cards"]) == len(
        flywheel["operator_next_actions"]
    )
    by_strength = {card["card"]: card for card in surface["strength_cards"]}
    assert by_strength["eight_chain_payment_integration"]["verification_badge"] == (
        "declared_not_reverified_by_this_artifact"
    )
    assert by_strength["eight_chain_payment_integration"][
        "may_be_repeated_as_freshly_reverified"
    ] is False
    assert {card["uses_axis"] for card in surface["connection_loop_cards"]} >= {
        "memory_system_to_acontext_bridge",
        "irc_session_management",
        "cross_project_decision_support",
        "agent_observability_success_metrics",
    }


def test_aas_system_integration_flywheel_read_surface_keeps_sticky_claim_footer():
    flywheel = build_aas_system_integration_flywheel()
    surface = build_aas_system_integration_flywheel_read_surface(flywheel=flywheel)
    footer = surface["claim_boundary_footer"]

    assert footer["placement"] == "sticky_after_every_recommendation"
    assert footer["safe_to_claim"] == surface["claim_boundaries"]["safe_to_claim"]
    assert footer["do_not_claim_yet"] == surface["claim_boundaries"]["do_not_claim_yet"]
    assert set(FLYWHEEL_BLOCKED_CLAIMS) <= set(footer["do_not_claim_yet"])
    assert set(SURFACE_BLOCKED_CLAIMS) <= set(footer["do_not_claim_yet"])
    assert not (set(footer["safe_to_claim"]) & set(footer["do_not_claim_yet"]))


def test_aas_system_integration_flywheel_read_surface_refuses_promoted_source():
    flywheel = deepcopy(build_aas_system_integration_flywheel())
    flywheel["readiness"]["acontext_sink_ready"] = True

    with pytest.raises(CityOpsContractError, match="promoted acontext_sink_ready"):
        build_aas_system_integration_flywheel_read_surface(flywheel=flywheel)


def test_aas_system_integration_flywheel_read_surface_refuses_payment_reverification():
    flywheel = deepcopy(build_aas_system_integration_flywheel())
    flywheel["derived_from"]["payment_system_reverified"] = True

    with pytest.raises(CityOpsContractError, match="payment-reverified source"):
        build_aas_system_integration_flywheel_read_surface(flywheel=flywheel)


def test_aas_system_integration_flywheel_read_surface_refuses_blocked_safe_claim():
    flywheel = deepcopy(build_aas_system_integration_flywheel())
    flywheel["claim_boundaries"]["safe_to_claim"].append("public_route_ready")

    with pytest.raises(CityOpsContractError, match="blocked claims marked safe"):
        build_aas_system_integration_flywheel_read_surface(flywheel=flywheel)


def test_aas_system_integration_flywheel_read_surface_loader_rejects_route_drift(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME,
        tmp_path / AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME,
    )
    path = write_aas_system_integration_flywheel_read_surface(artifact_dir=tmp_path)
    surface = json.loads(path.read_text(encoding="utf-8"))
    surface["render_contract"]["network_route_registered"] = True
    path.write_text(json.dumps(surface), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="network route"):
        load_aas_system_integration_flywheel_read_surface(artifact_dir=tmp_path)


def test_aas_system_integration_flywheel_read_surface_write_and_load_temp_fixture(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME,
        tmp_path / AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME,
    )
    path = write_aas_system_integration_flywheel_read_surface(artifact_dir=tmp_path)

    assert path.name == AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_FILENAME
    loaded = load_aas_system_integration_flywheel_read_surface(artifact_dir=tmp_path)
    assert loaded["schema"] == AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_SAFE_CLAIM
    )
