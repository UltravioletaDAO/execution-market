"""Tests for the Acontext root-prefixed local write/retrieve parity proof."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_project_secret_path_resolution_decision import (
    ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_FILENAME,
    build_acontext_project_secret_path_resolution_decision,
)
from mcp_server.city_ops.acontext_root_prefixed_local_write_retrieve_parity import (
    ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME,
    ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SAFE_CLAIM,
    ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SCHEMA,
    ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_STOP_LINE,
    build_acontext_root_prefixed_local_write_retrieve_parity,
    load_acontext_root_prefixed_local_write_retrieve_parity,
    write_acontext_root_prefixed_local_write_retrieve_parity,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_PROJECT_SECRET_PATH_RESOLUTION_DECISION_FILENAME).exists()


def test_build_root_prefixed_local_parity_records_success_without_secrets(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)

    assert artifact["schema"] == ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SCHEMA
    assert artifact["observation_verdict"] == (
        "local_acontext_write_retrieve_parity_succeeded_with_root_prefixed_bearer_route_mismatch_still_unresolved"
    )
    assert ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_SAFE_CLAIM in artifact["claim_boundaries"][
        "safe_to_claim"
    ]
    assert artifact["derived_from"]["uses_running_local_stack"] is True
    assert artifact["derived_from"]["uses_root_prefixed_bearer_in_memory_only"] is True
    assert artifact["derived_from"]["persists_or_prints_secret"] is False
    assert artifact["readiness"]["root_prefixed_bearer_supported_for_local_api"] is True
    assert artifact["readiness"]["local_write_retrieve_parity_proven"] is True
    assert artifact["readiness"]["scoped_project_secret_created_or_acquired"] is False
    assert artifact["readiness"]["admin_project_route_still_unresolved"] is True


def test_root_prefixed_local_parity_preserves_existing_boundaries(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    source = build_acontext_project_secret_path_resolution_decision(artifact_dir=tmp_path)
    artifact = build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)
    inherited = source["claim_boundaries"]["do_not_claim_yet"]

    assert artifact["claim_boundary_audit"]["inherited_do_not_claim_yet"] == inherited
    assert artifact["claim_boundaries"]["do_not_claim_yet"][: len(inherited)] == inherited
    assert set(inherited) <= set(artifact["claim_boundaries"]["do_not_claim_yet"])
    assert not set(artifact["claim_boundaries"]["safe_to_claim"]) & set(
        artifact["claim_boundaries"]["do_not_claim_yet"]
    )


def test_root_prefixed_local_parity_keeps_all_secret_and_identifier_values_out(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)
    observation = artifact["runtime_observation"]

    assert observation["credential_path_discovery"]["root_token_value_printed"] is False
    assert observation["credential_path_discovery"]["derived_bearer_value_printed"] is False
    assert observation["credential_path_discovery"]["derived_bearer_value_persisted"] is False
    assert observation["credential_path_discovery"]["scoped_project_secret_created"] is False
    assert observation["local_probe"]["create_session"]["session_id_recorded"] is False
    assert observation["local_probe"]["create_session"]["project_id_recorded"] is False
    assert observation["local_probe"]["store_message"]["message_id_recorded"] is False
    assert observation["sanitization_policy"]["include_session_id"] is False
    assert observation["sanitization_policy"]["include_message_id"] is False

    serialized = json.dumps(artifact).lower()
    assert "authorization: bearer sk-ac-${root_api_bearer_token}" in serialized
    assert re.search(r"bearer sk-ac-[a-z0-9]{8,}", serialized) is None
    assert "root_api_bearer_token=" not in serialized
    assert "secret_key_hmac" not in serialized
    assert "secret_key_hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None


def test_root_prefixed_local_parity_records_exact_local_http_successes(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)
    probe = artifact["runtime_observation"]["local_probe"]

    assert probe["create_session"]["status_code"] == 201
    assert probe["store_message"]["status_code"] == 201
    assert probe["retrieve_messages"]["status_code"] == 200
    assert probe["retrieve_messages"]["retrieved_message_count"] == 1
    assert probe["retrieve_messages"]["retrieved_message_text_matches"] is True
    assert probe["retrieve_messages"]["retrieved_message_meta_matches"] is True
    assert all(gate["passed"] is True for gate in artifact["parity_gates"])
    assert all(gate["authorizes_customer_or_dispatch_claim"] is False for gate in artifact["parity_gates"])


def test_root_prefixed_local_parity_blocks_customer_dispatch_reputation_payment_and_doctrine(
    tmp_path: Path,
) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)
    blocked = artifact["claim_boundaries"]["do_not_claim_yet"]
    safe = artifact["claim_boundaries"]["safe_to_claim"]

    for required_fragment in [
        "authorizes_customer_copy_delivery_or_publication",
        "authorizes_public_or_catalog_route",
        "authorizes_queue_launch_or_dispatch",
        "authorizes_reputation_or_worker_skill_dna",
        "reverifies_payment_or_production",
        "allows_exact_gps_or_raw_metadata",
        "releases_private_operator_context",
        "creates_worker_copyable_doctrine",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)

    assert all(flag is False for flag in artifact["access_flags"].values())


def test_root_prefixed_local_parity_stop_line_remains_narrow(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    artifact = build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)

    assert artifact["operator_guidance"]["stop_line"] == ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_STOP_LINE
    assert "customer/public delivery" in artifact["operator_guidance"]["stop_line"]
    assert "IRC session-manager mutation" in artifact["operator_guidance"]["stop_line"]
    assert artifact["readiness"]["irc_runtime_session_manager_ready"] is False
    assert artifact["readiness"]["cross_project_autorouting_ready"] is False


def test_write_and_load_root_prefixed_local_parity_fixture_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_ROOT_PREFIXED_LOCAL_PARITY_FILENAME
    loaded = load_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)
    assert loaded == build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)


def test_root_prefixed_local_parity_fixture_drift_is_rejected(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["readiness"]["customer_or_public_delivery_ready"] = True
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="fixture drift"):
        load_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)


def test_root_prefixed_local_parity_rejects_secret_leak_or_failed_retrieval(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    observation = build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)[
        "runtime_observation"
    ]
    observation["credential_path_discovery"]["derived_bearer_value_printed"] = True

    with pytest.raises(CityOpsContractError, match="derived_bearer_value_printed"):
        build_acontext_root_prefixed_local_write_retrieve_parity(
            artifact_dir=tmp_path,
            observation=observation,
        )

    observation = build_acontext_root_prefixed_local_write_retrieve_parity(artifact_dir=tmp_path)[
        "runtime_observation"
    ]
    observation["local_probe"]["retrieve_messages"]["status_code"] = 500

    with pytest.raises(CityOpsContractError, match="retrieve_messages"):
        build_acontext_root_prefixed_local_write_retrieve_parity(
            artifact_dir=tmp_path,
            observation=observation,
        )
