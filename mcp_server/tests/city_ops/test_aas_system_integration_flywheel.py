import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from mcp_server.city_ops.aas_system_integration_flywheel import (
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_SAFE_CLAIM,
    AAS_SYSTEM_INTEGRATION_FLYWHEEL_SCHEMA,
    FLYWHEEL_BLOCKED_CLAIMS,
    REQUIRED_AXES,
    build_aas_system_integration_flywheel,
    load_aas_system_integration_flywheel,
    write_aas_system_integration_flywheel,
)
from mcp_server.city_ops.contracts import CityOpsContractError
from mcp_server.city_ops.decision_support_readiness_matrix import (
    build_decision_support_readiness_matrix,
)

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_flywheel() -> dict:
    with (PROOF_BLOCK_DIR / AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_aas_system_integration_flywheel_matches_fixture():
    flywheel = build_aas_system_integration_flywheel()

    assert flywheel == read_fixture_flywheel()
    assert flywheel["schema"] == AAS_SYSTEM_INTEGRATION_FLYWHEEL_SCHEMA
    assert flywheel["flywheel_verdict"] == (
        "system_integration_flywheel_landed_live_acontext_blocked"
    )
    assert AAS_SYSTEM_INTEGRATION_FLYWHEEL_SAFE_CLAIM in flywheel["claim_boundaries"][
        "safe_to_claim"
    ]
    assert flywheel["readiness"]["flywheel_artifact_ready"] is True
    assert flywheel["readiness"]["flywheel_promotes_live_readiness"] is False
    assert flywheel["readiness"]["acontext_sink_ready"] is False
    assert flywheel["readiness"]["payment_coverage_reverified_by_this_artifact"] is False


def test_aas_system_integration_flywheel_connects_all_required_axes_and_strengths():
    flywheel = build_aas_system_integration_flywheel()
    loops = flywheel["connection_loops"]
    axes = {loop["uses_axis"] for loop in loops}
    strengths = {item["strength"] for item in flywheel["declared_strength_inputs"]}

    assert axes == set(REQUIRED_AXES)
    assert len(loops) == 5
    assert strengths == {
        "latest_city_ops_code_changes",
        "eight_chain_payment_integration",
        "intelligent_memory_with_26_plus_insights",
        "production_infrastructure_operational",
        "legendary_agent_coordination",
    }
    assert flywheel["system_integration_metrics"]["required_axis_count"] == 4
    assert flywheel["system_integration_metrics"]["ready_axis_count_from_matrix"] == 3
    assert flywheel["system_integration_metrics"]["blocked_axis_count_from_matrix"] == 1
    assert flywheel["system_integration_metrics"]["claim_boundary_preservation"] == "pass"


def test_aas_system_integration_flywheel_labels_declared_not_reverified_strengths():
    flywheel = build_aas_system_integration_flywheel()
    by_strength = {item["strength"]: item for item in flywheel["declared_strength_inputs"]}

    assert by_strength["eight_chain_payment_integration"]["verification_level"] == (
        "declared_not_reverified_by_this_artifact"
    )
    assert by_strength["production_infrastructure_operational"]["verification_level"] == (
        "declared_not_reverified_by_this_artifact"
    )
    assert flywheel["derived_from"]["payment_system_reverified"] is False
    assert flywheel["derived_from"]["production_infrastructure_reverified"] is False
    assert "payment_coverage_reverified_by_this_artifact" in flywheel["claim_boundaries"][
        "do_not_claim_yet"
    ]


def test_aas_system_integration_flywheel_preserves_blocked_claims():
    matrix = build_decision_support_readiness_matrix()
    flywheel = build_aas_system_integration_flywheel(decision_support_matrix=matrix)

    inherited_blocked = set(matrix["claim_boundaries"]["do_not_claim_yet"])
    flywheel_blocked = set(flywheel["claim_boundaries"]["do_not_claim_yet"])

    assert inherited_blocked <= flywheel_blocked
    assert set(FLYWHEEL_BLOCKED_CLAIMS) <= flywheel_blocked
    assert not (flywheel_blocked & set(flywheel["claim_boundaries"]["safe_to_claim"]))


def test_aas_system_integration_flywheel_accepts_attemptable_transport_without_promotion():
    matrix = build_decision_support_readiness_matrix()
    matrix["readiness"]["ready_to_attempt_live_transport"] = True
    matrix["readiness"]["local_transport_parity_fixture_passed"] = True
    matrix["readiness"]["blockers"] = []
    for axis in matrix["handoff_axes"]:
        if axis["axis"] == "memory_system_to_acontext_bridge":
            axis["state"] = "attemptable_not_ready"

    flywheel = build_aas_system_integration_flywheel(decision_support_matrix=matrix)

    assert flywheel["flywheel_verdict"] == (
        "system_integration_flywheel_landed_live_acontext_attemptable_not_ready"
    )
    assert flywheel["readiness"]["ready_to_attempt_live_transport"] is True
    assert flywheel["readiness"]["acontext_sink_ready"] is False
    assert flywheel["readiness"]["runtime_parity_proven"] is False


def test_aas_system_integration_flywheel_refuses_promoted_acontext_readiness():
    matrix = build_decision_support_readiness_matrix()
    matrix["readiness"]["acontext_sink_ready"] = True

    with pytest.raises(CityOpsContractError, match="Acontext readiness"):
        build_aas_system_integration_flywheel(decision_support_matrix=matrix)


def test_aas_system_integration_flywheel_refuses_blocked_safe_claim():
    matrix = build_decision_support_readiness_matrix()
    matrix["claim_boundaries"]["safe_to_claim"].append("live_acontext_sink_ready")

    with pytest.raises(CityOpsContractError, match="blocked claims marked safe"):
        build_aas_system_integration_flywheel(decision_support_matrix=matrix)


def test_aas_system_integration_flywheel_refuses_missing_axis():
    matrix = deepcopy(build_decision_support_readiness_matrix())
    matrix["handoff_axes"] = [
        axis for axis in matrix["handoff_axes"] if axis["axis"] != "irc_session_management"
    ]

    with pytest.raises(CityOpsContractError, match="missing axes"):
        build_aas_system_integration_flywheel(decision_support_matrix=matrix)


def test_aas_system_integration_flywheel_write_and_load_temp_fixture(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / "decision_support_readiness_matrix.json",
        tmp_path / "decision_support_readiness_matrix.json",
    )
    path = write_aas_system_integration_flywheel(artifact_dir=tmp_path)

    assert path.name == AAS_SYSTEM_INTEGRATION_FLYWHEEL_FILENAME
    loaded = load_aas_system_integration_flywheel(artifact_dir=tmp_path)
    assert loaded["schema"] == AAS_SYSTEM_INTEGRATION_FLYWHEEL_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        AAS_SYSTEM_INTEGRATION_FLYWHEEL_SAFE_CLAIM
    )


def test_aas_system_integration_flywheel_loader_rejects_payment_reverification(tmp_path):
    shutil.copy(
        PROOF_BLOCK_DIR / "decision_support_readiness_matrix.json",
        tmp_path / "decision_support_readiness_matrix.json",
    )
    path = write_aas_system_integration_flywheel(artifact_dir=tmp_path)
    flywheel = json.loads(path.read_text(encoding="utf-8"))
    flywheel["derived_from"]["payment_system_reverified"] = True
    path.write_text(json.dumps(flywheel), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="reverify payments"):
        load_aas_system_integration_flywheel(artifact_dir=tmp_path)
