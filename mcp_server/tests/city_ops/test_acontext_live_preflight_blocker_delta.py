import copy
import json
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_live_preflight import (
    build_acontext_live_preflight_result,
)
from mcp_server.city_ops.acontext_live_preflight_blocker_delta import (
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME,
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SAFE_CLAIM,
    ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SCHEMA,
    BASELINE_BLOCKERS,
    BLOCKER_DELTA_BLOCKED_CLAIMS,
    build_acontext_live_preflight_blocker_delta,
    build_may15_7am_partial_acontext_probe,
    load_acontext_live_preflight_blocker_delta,
    write_acontext_live_preflight_blocker_delta,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_delta() -> dict:
    with (PROOF_BLOCK_DIR / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def test_acontext_live_preflight_blocker_delta_matches_fixture():
    delta = build_acontext_live_preflight_blocker_delta()

    assert delta == read_delta()
    assert load_acontext_live_preflight_blocker_delta() == delta
    assert delta["schema"] == ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SCHEMA
    assert ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_SAFE_CLAIM in delta[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert delta["delta_verdict"] == (
        "live_transport_still_blocked_with_partial_prerequisite_progress"
    )


def test_delta_records_docker_cleared_but_sdk_api_dashboard_still_blocked():
    delta = build_acontext_live_preflight_blocker_delta()

    assert delta["baseline_blockers"] == BASELINE_BLOCKERS
    assert delta["cleared_blockers"] == ["docker_daemon_unavailable"]
    assert delta["remaining_blockers"] == [
        "acontext_python_sdk_missing",
        "local_acontext_api_unreachable",
        "local_acontext_dashboard_unreachable",
    ]
    assert delta["newly_blocked"] == []
    by_prereq = {card["prerequisite"]: card for card in delta["prerequisite_cards"]}
    assert by_prereq["docker_daemon"]["status"] == "cleared"
    assert by_prereq["acontext_python_sdk"]["status"] == "blocked"
    assert by_prereq["local_acontext_api"]["status"] == "blocked"
    assert by_prereq["local_acontext_dashboard"]["status"] == "blocked"


def test_delta_keeps_live_runtime_customer_dispatch_reputation_claims_blocked():
    delta = build_acontext_live_preflight_blocker_delta()

    readiness = delta["readiness"]
    assert readiness["blocker_delta_landed"] is True
    assert readiness["docker_available"] is True
    assert readiness["ready_to_attempt_live_transport"] is False
    assert readiness["acontext_sink_ready"] is False
    assert readiness["runtime_parity_proven"] is False
    assert readiness["live_acontext_write_performed"] is False
    assert readiness["live_acontext_retrieval_performed"] is False
    assert readiness["customer_visible_aas_packaging_ready"] is False
    assert readiness["public_route_ready"] is False
    assert readiness["autonomous_dispatch_ready"] is False
    assert readiness["erc8004_reputation_ready"] is False
    for claim in BLOCKER_DELTA_BLOCKED_CLAIMS:
        assert claim in delta["claim_boundaries"]["do_not_claim_yet"]
        assert claim not in delta["claim_boundaries"]["safe_to_claim"]


def test_write_delta_persists_valid_artifact(tmp_path):
    preflight = build_acontext_live_preflight_result(
        probe=build_may15_7am_partial_acontext_probe()
    )
    path = write_acontext_live_preflight_blocker_delta(
        artifact_dir=tmp_path, preflight=preflight
    )

    assert path == tmp_path / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME
    loaded = load_acontext_live_preflight_blocker_delta(artifact_dir=tmp_path)
    assert loaded == json.loads(path.read_text(encoding="utf-8"))


def test_source_that_is_ready_to_attempt_live_transport_is_not_a_blocker_delta():
    preflight = build_acontext_live_preflight_result(
        probe={
            "docker": {"checked": True, "available": True, "exit_code": 0, "error": None},
            "python_sdk": {"checked": True, "package": "acontext", "available": True},
            "api": {
                "checked": True,
                "url": "http://localhost:8029/api/v1",
                "reachable": True,
                "status_code": 200,
                "error": None,
            },
            "dashboard": {
                "checked": True,
                "url": "http://localhost:3000",
                "reachable": True,
                "status_code": 200,
                "error": None,
            },
            "live_acontext_write_performed": False,
            "live_acontext_retrieval_performed": False,
        }
    )

    with pytest.raises(CityOpsContractError, match="cannot replace a ready live parity run"):
        build_acontext_live_preflight_blocker_delta(preflight=preflight)


def test_source_with_live_write_fails_closed():
    preflight = build_acontext_live_preflight_result(
        probe=build_may15_7am_partial_acontext_probe()
    )
    preflight["readiness"] = copy.deepcopy(preflight["readiness"])
    preflight["readiness"]["live_acontext_write_performed"] = True

    with pytest.raises(CityOpsContractError, match="live write source"):
        build_acontext_live_preflight_blocker_delta(preflight=preflight)


def test_source_forbidden_safe_claim_fails_closed():
    preflight = build_acontext_live_preflight_result(
        probe=build_may15_7am_partial_acontext_probe()
    )
    preflight["claim_boundaries"] = copy.deepcopy(preflight["claim_boundaries"])
    preflight["claim_boundaries"]["safe_to_claim"].append("live_acontext_sink_ready")

    with pytest.raises(CityOpsContractError, match="forbidden safe claims"):
        build_acontext_live_preflight_blocker_delta(preflight=preflight)


def test_loader_fails_closed_on_readiness_promotion(tmp_path):
    delta = build_acontext_live_preflight_blocker_delta()
    delta["readiness"]["runtime_parity_proven"] = True
    (tmp_path / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME).write_text(
        json.dumps(delta), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_acontext_live_preflight_blocker_delta(artifact_dir=tmp_path)


def test_loader_fails_closed_on_card_authorizing_live_write(tmp_path):
    delta = build_acontext_live_preflight_blocker_delta()
    delta["prerequisite_cards"][0]["authorizes_live_write"] = True
    (tmp_path / ACONTEXT_LIVE_PREFLIGHT_BLOCKER_DELTA_FILENAME).write_text(
        json.dumps(delta), encoding="utf-8"
    )

    with pytest.raises(CityOpsContractError, match="authorized live write"):
        load_acontext_live_preflight_blocker_delta(artifact_dir=tmp_path)
