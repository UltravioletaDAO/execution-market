"""Tests for the Acontext project-secret path resolution decision."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_project_admin_route_mismatch_observation import (
    ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_FILENAME,
    build_acontext_project_admin_route_mismatch_observation,
)
from mcp_server.city_ops.acontext_project_secret_path_resolution_decision import (
    ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_FILENAME,
    ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SAFE_CLAIM,
    ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SCHEMA,
    ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_STOP_LINE,
    build_acontext_project_secret_path_resolution_decision,
    load_acontext_project_secret_path_resolution_decision,
    write_acontext_project_secret_path_resolution_decision,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_PROJECT_ADMIN_ROUTE_MISMATCH_FILENAME).exists()


def test_build_project_secret_path_resolution_records_current_blocker(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)

    assert artifact["schema"] == ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SCHEMA
    assert artifact["observation_verdict"] == (
        "project_secret_path_resolution_still_blocked_route_mount_or_supported_non_admin_secret_path_inspection_required"
    )
    assert ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_SAFE_CLAIM in artifact["claim_boundaries"][
        "safe_to_claim"
    ]
    assert artifact["derived_from"]["requires_live_acontext"] is False
    assert artifact["derived_from"]["runtime_observation_performed"] is False
    assert artifact["readiness"]["known_admin_project_route_status_404"] is True
    assert artifact["readiness"]["project_secret_path_resolved"] is False
    assert artifact["readiness"]["project_bearer_available_to_probe"] is False
    assert artifact["readiness"]["runtime_parity_proven"] is False


def test_project_secret_path_resolution_preserves_exact_inherited_blocked_claims(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    source = build_acontext_project_admin_route_mismatch_observation(artifact_dir=tmp_path)
    artifact = build_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)
    inherited = source["claim_boundaries"]["do_not_claim_yet"]

    assert artifact["claim_boundary_audit"]["inherited_do_not_claim_yet"] == inherited
    assert artifact["claim_boundaries"]["do_not_claim_yet"][: len(inherited)] == inherited
    assert set(inherited) <= set(artifact["claim_boundaries"]["do_not_claim_yet"])
    assert not set(artifact["claim_boundaries"]["safe_to_claim"]) & set(
        artifact["claim_boundaries"]["do_not_claim_yet"]
    )


def test_project_secret_path_resolution_keeps_secret_values_out(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)
    observation = artifact["runtime_observation"]

    assert observation["does_not_require_live_acontext"] is True
    assert observation["does_not_repeat_live_probe"] is True
    assert observation["source_runtime_truth"]["project_bearer_secret_acquired"] is False
    assert observation["source_runtime_truth"]["project_bearer_secret_recorded"] is False
    assert observation["sanitization_policy"]["include_project_secret_value"] is False
    assert observation["path_resolution_decision"]["request_or_store_project_secret"] is False

    serialized = json.dumps(artifact).lower()
    assert "bearer sk-" not in serialized
    assert "root_api_bearer_token=" not in serialized
    assert "secret_key_hmac" not in serialized
    assert "secret_key_hash_phc" not in serialized


def test_project_secret_path_resolution_blocks_public_dispatch_reputation_payment_and_doctrine(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)
    blocked = artifact["claim_boundaries"]["do_not_claim_yet"]
    safe = artifact["claim_boundaries"]["safe_to_claim"]

    for required_fragment in [
        "authorizes_customer_copy_delivery_or_publication",
        "authorizes_public_or_catalog_route",
        "authorizes_queue_launch_or_dispatch",
        "authorizes_reputation_or_worker_skill_dna",
        "reverifies_payment_or_production",
        "creates_worker_copyable_doctrine",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)

    assert all(flag is False for flag in artifact["access_flags"].values())
    assert all(gate["authorizes_customer_or_dispatch_claim"] is False for gate in artifact["resolution_gates"])


def test_project_secret_path_resolution_stop_line_holds_when_unresolved(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)

    assert artifact["operator_guidance"]["stop_line"] == ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_STOP_LINE
    assert artifact["runtime_observation"]["path_resolution_decision"]["stop_line"] == (
        ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_STOP_LINE
    )
    assert artifact["runtime_observation"]["path_resolution_decision"]["current_route_state"] == "unresolved"
    assert artifact["runtime_observation"]["path_resolution_decision"]["run_write_retrieve_parity_smoke"] is False


def test_write_and_load_project_secret_path_resolution_fixture_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_FILENAME
    loaded = load_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)
    assert loaded == build_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)


def test_project_secret_path_resolution_fixture_drift_is_rejected(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["project_secret_path_resolved"] = True
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)


def test_project_secret_path_resolution_rejects_route_or_secret_promotion(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    observation = build_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)[
        "runtime_observation"
    ]
    observation["source_runtime_truth"]["runtime_probe_statuses"][0]["status_code"] = 200

    with pytest.raises(CityOpsContractError, match="404"):
        build_acontext_project_secret_path_resolution_decision(
            artifact_dir=tmp_path,
            observation=observation,
        )

    observation = build_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)[
        "runtime_observation"
    ]
    observation["path_resolution_decision"]["request_or_store_project_secret"] = True

    with pytest.raises(CityOpsContractError, match="request_or_store_project_secret"):
        build_acontext_project_secret_path_resolution_decision(
            artifact_dir=tmp_path,
            observation=observation,
        )
