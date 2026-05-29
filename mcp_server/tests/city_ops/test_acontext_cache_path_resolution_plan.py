from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_cache_path_resolution_plan import (
    ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_FILENAME,
    ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SAFE_CLAIM,
    ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SCHEMA,
    CACHE_PATH_RESOLUTION_PLAN_BLOCKED_CLAIMS,
    CACHE_PATH_RESOLUTION_PLAN_VERDICT,
    build_acontext_cache_path_resolution_plan,
    load_acontext_cache_path_resolution_plan,
    write_acontext_cache_path_resolution_plan,
)
from mcp_server.city_ops.acontext_image_cache_path_probe import (
    ACONTEXT_IMAGE_CACHE_PATH_PROBE_SAFE_CLAIM,
    build_acontext_image_cache_path_probe,
)
from mcp_server.city_ops.contracts import CityOpsContractError

FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def read_fixture_plan() -> dict:
    return json.loads(
        (PROOF_BLOCK_DIR / ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_FILENAME).read_text(
            encoding="utf-8"
        )
    )


def test_cache_path_resolution_plan_matches_fixture_and_loader():
    plan = build_acontext_cache_path_resolution_plan()

    assert plan == read_fixture_plan()
    assert load_acontext_cache_path_resolution_plan() == plan
    assert plan["schema"] == ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SCHEMA
    assert plan["plan_verdict"] == CACHE_PATH_RESOLUTION_PLAN_VERDICT
    safe = plan["claim_boundaries"]["safe_to_claim"]
    assert ACONTEXT_IMAGE_CACHE_PATH_PROBE_SAFE_CLAIM in safe
    assert ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SAFE_CLAIM in safe


def test_cache_path_resolution_plan_selects_one_changed_path_without_executing_it():
    plan = build_acontext_cache_path_resolution_plan()
    derived = plan["derived_from"]
    options = plan["resolution_options"]
    readiness = plan["readiness"]

    assert plan["selected_next_changed_cache_path"] == (
        "trusted_registry_client_export_load_path"
    )
    assert [option["rank"] for option in options] == [1, 2, 3, 4, 5]
    assert options[0]["option"] == "trusted_registry_client_export_load_path"
    assert options[0]["candidate_tools"] == ["crane", "oras", "skopeo", "regctl"]
    assert all(option["requires_operator_approval_before_execution"] is True for option in options)
    assert all(option["executes_in_this_artifact"] is False for option in options)
    assert all(option["authorizes_compose_startup"] is False for option in options)
    assert all(option["authorizes_live_parity"] is False for option in options)
    assert derived["runtime_observation_performed"] is False
    assert derived["installs_registry_tooling"] is False
    assert derived["uses_registry_tooling"] is False
    assert derived["pulls_container_image"] is False
    assert readiness["selected_next_changed_cache_path"] is True
    assert readiness["registry_tool_installed"] is False
    assert readiness["registry_tool_used"] is False


def test_cache_path_resolution_plan_preserves_gate_order_and_blocks_runtime():
    plan = build_acontext_cache_path_resolution_plan()
    gates = plan["post_selection_gate_order"]

    assert [gate["gate"] for gate in gates] == [
        "operator_cache_path_selection",
        "bounded_cache_attempt_execution",
        "first_required_image_inventory",
        "all_required_images_inventory",
        "local_acontext_services_health",
        "read_only_preflight_rebuild",
        "single_live_write_retrieve_parity_attempt",
    ]
    assert gates[0]["passed"] is True
    assert all(gate["passed"] is False for gate in gates[1:])
    assert all(gate["authorizes_live_attempt"] is False for gate in gates)
    assert plan["readiness"]["first_required_image_present"] is False
    assert plan["readiness"]["all_required_images_present"] is False
    assert plan["readiness"]["compose_services_started"] is False
    assert plan["readiness"]["acontext_api_reachable"] is False
    assert plan["readiness"]["memory_acontext_parity_ready"] is False


def test_cache_path_resolution_plan_preserves_blocked_claims():
    plan = build_acontext_cache_path_resolution_plan()

    safe = set(plan["claim_boundaries"]["safe_to_claim"])
    blocked = set(plan["claim_boundaries"]["do_not_claim_yet"])
    assert safe.isdisjoint(blocked)
    assert set(CACHE_PATH_RESOLUTION_PLAN_BLOCKED_CLAIMS) <= blocked
    assert "cache_path_resolution_plan_installed_registry_tooling" in blocked
    assert "cache_path_resolution_plan_cached_first_required_image" in blocked
    assert "cache_path_resolution_plan_started_compose_services" in blocked
    assert "cache_path_resolution_plan_completed_live_acontext_write" in blocked
    assert "cache_path_resolution_plan_proved_runtime_parity" in blocked
    assert "cache_path_resolution_plan_authorizes_customer_copy_delivery_or_publication" in blocked


def test_cache_path_resolution_plan_refuses_source_with_promoted_tooling():
    source = copy.deepcopy(build_acontext_image_cache_path_probe())
    source["readiness"]["registry_tool_install_performed"] = True

    with pytest.raises(CityOpsContractError, match="source promoted later readiness"):
        build_acontext_cache_path_resolution_plan(cache_path_probe=source)


def test_cache_path_resolution_plan_refuses_executed_option_in_fixture_shape():
    plan = copy.deepcopy(read_fixture_plan())
    source = build_acontext_image_cache_path_probe()
    plan["resolution_options"][0]["executes_in_this_artifact"] = True

    with pytest.raises(CityOpsContractError, match="must not execute options"):
        from mcp_server.city_ops.acontext_cache_path_resolution_plan import (
            _assert_artifact_conservative,
        )

        _assert_artifact_conservative(plan, source)


def test_cache_path_resolution_plan_write_and_load_temp_fixture(tmp_path):
    _copy_probe_sources(tmp_path)
    path = write_acontext_cache_path_resolution_plan(artifact_dir=tmp_path)

    assert path.name == ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_FILENAME
    loaded = load_acontext_cache_path_resolution_plan(artifact_dir=tmp_path)
    assert loaded["schema"] == ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SCHEMA
    assert loaded["claim_boundaries"]["safe_to_claim"][-1] == (
        ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_SAFE_CLAIM
    )


def test_cache_path_resolution_plan_loader_rejects_drift(tmp_path):
    _copy_probe_sources(tmp_path)
    path = write_acontext_cache_path_resolution_plan(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["first_required_image_present"] = True
    path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="promoted readiness"):
        load_acontext_cache_path_resolution_plan(artifact_dir=tmp_path)


def _copy_probe_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_CACHE_PATH_RESOLUTION_PLAN_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
