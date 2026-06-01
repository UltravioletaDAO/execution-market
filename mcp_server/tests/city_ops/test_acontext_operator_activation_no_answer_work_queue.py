"""Tests for the Acontext no-answer activation work queue."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_operator_activation_answer_schema_gate import (
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM,
    build_acontext_operator_activation_answer_schema_gate,
)
from mcp_server.city_ops.acontext_operator_activation_no_answer_work_queue import (
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SCHEMA,
    ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_STOP_LINE,
    NO_ANSWER_WORK_QUEUE_BLOCKED_CLAIMS,
    build_acontext_operator_activation_no_answer_work_queue,
    load_acontext_operator_activation_no_answer_work_queue,
    write_acontext_operator_activation_no_answer_work_queue,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME).exists()


def test_no_answer_work_queue_matches_fixture() -> None:
    queue = build_acontext_operator_activation_no_answer_work_queue()
    with (PROOF_BLOCK_DIR / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert queue == fixture
    assert load_acontext_operator_activation_no_answer_work_queue() == queue
    assert queue["schema"] == ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SCHEMA
    assert queue["status_verdict"] == "no_answer_work_queue_landed_default_hold_preserved_no_runtime_mutation"
    assert ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM in queue[
        "claim_boundaries"
    ]["safe_to_claim"]
    assert ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_SAFE_CLAIM in queue[
        "claim_boundaries"
    ]["safe_to_claim"]


def test_no_answer_work_queue_preserves_hold_and_records_no_approval() -> None:
    queue = build_acontext_operator_activation_no_answer_work_queue()
    posture = queue["no_answer_runtime_posture"]

    assert queue["activation_candidate"]["candidate_id"] == "irc_session_manager_memory_sink"
    assert posture["explicit_operator_answer_present"] is False
    assert posture["operator_approval_record_present"] is False
    assert posture["answer_schema_validated"] is False
    assert posture["effective_decision"] == "hold_no_runtime_mutation"
    assert posture["runtime_mutation_authorized"] is False
    assert posture["bounded_activation_test_authorized"] is False
    assert posture["this_queue_is_not_an_approval_record"] is True


def test_no_answer_work_queue_allows_only_internal_admin_safe_work() -> None:
    queue = build_acontext_operator_activation_no_answer_work_queue()
    work_ids = {item["work_id"] for item in queue["allowed_internal_work_queue"]}

    assert work_ids == {
        "display_internal_admin_hold_and_answer_schema",
        "validate_future_answer_shape_only",
        "continue_read_only_docs_or_fixture_review",
    }
    for item in queue["allowed_internal_work_queue"]:
        assert item["records_approval"] is False
        assert item["runtime_mutation"] is False
        assert item["customer_or_worker_exposure"] == "none"


def test_no_answer_work_queue_preserves_stopped_project_firewall() -> None:
    queue = build_acontext_operator_activation_no_answer_work_queue()
    firewall = queue["stopped_project_firewall"]

    assert firewall["autojob_work_allowed"] is False
    assert firewall["frontier_academy_work_allowed"] is False
    assert firewall["kk_v2_work_allowed"] is False
    assert firewall["karmacadabra_v2_work_allowed"] is False
    assert firewall["source"] == "DREAM-PRIORITIES.md explicit stop list"


def test_no_answer_work_queue_keeps_runtime_and_external_surfaces_blocked() -> None:
    queue = build_acontext_operator_activation_no_answer_work_queue()
    readiness = queue["readiness"]

    assert readiness["safe_for_internal_admin_no_answer_work_queue_display"] is True
    for key in [
        "safe_for_runtime_adapter_registration",
        "safe_for_runtime_adapter_enablement",
        "safe_for_runtime_session_manager_mutation",
        "safe_for_bounded_activation_test_execution",
        "safe_for_cross_project_autorouting",
        "safe_for_customer_or_public_delivery",
        "safe_for_queue_launch_or_dispatch",
        "safe_for_reputation_or_worker_skill_dna",
        "safe_for_payment_or_production_claim",
        "safe_for_gps_or_raw_metadata_release",
        "safe_for_private_context_release",
        "safe_for_domain_legal_emergency_repair_insurance_or_sla_authority",
        "safe_for_worker_copyable_doctrine",
        "safe_for_stopped_project_integration",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
        "operator_activation_approved",
    ]:
        assert readiness[key] is False
    assert all(flag is False for flag in queue["access_flags"].values())


def test_no_answer_work_queue_preserves_blocked_claim_boundaries() -> None:
    queue = build_acontext_operator_activation_no_answer_work_queue()
    blocked = set(queue["claim_boundaries"]["do_not_claim_yet"])
    safe = set(queue["claim_boundaries"]["safe_to_claim"])

    assert set(NO_ANSWER_WORK_QUEUE_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_answer",
        "records_operator_approval",
        "runtime_adapter_registration",
        "runtime_adapter_enablement",
        "irc_session_manager_mutation",
        "bounded_local_activation_test",
        "cross_project_autorouting",
        "customer_copy_delivery_or_publication",
        "queue_launch_or_dispatch",
        "erc8004_reputation",
        "worker_skill_dna",
        "exact_gps_or_raw_metadata",
        "private_operator_context",
        "worker_copyable_doctrine",
        "stopped_project_integration",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)


def test_no_answer_work_queue_persists_no_secret_ids_payload_or_pii() -> None:
    queue = build_acontext_operator_activation_no_answer_work_queue()
    serialized = json.dumps(queue).lower()

    assert "bearer " + "sk" + "-ac-" not in serialized
    assert "root_api" + "_bearer_token=" not in serialized
    assert "secret" + "_key_" + "hmac" not in serialized
    assert "secret" + "_key_" + "hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None
    assert "@" not in serialized
    assert "sanitized message" not in serialized
    assert "redacted_session_id" not in serialized
    assert "redacted_message_id" not in serialized


def test_no_answer_work_queue_stop_line_remains_fail_closed() -> None:
    queue = build_acontext_operator_activation_no_answer_work_queue()

    assert queue["operator_guidance"]["stop_line"] == ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_STOP_LINE
    assert "records no answer" in queue["operator_guidance"]["stop_line"]
    assert "does not authorize runtime adapter registration" in queue["operator_guidance"]["stop_line"]
    assert queue["operator_guidance"]["not_customer_copy"] is True
    assert queue["operator_guidance"]["not_worker_instruction"] is True
    assert queue["operator_guidance"]["if_no_human_answer"] == "stay_on_hold_or_do_read_only_internal_admin_review_only"


def test_no_answer_work_queue_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_operator_activation_no_answer_work_queue(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_WORK_QUEUE_FILENAME
    loaded = load_acontext_operator_activation_no_answer_work_queue(artifact_dir=tmp_path)
    assert loaded == build_acontext_operator_activation_no_answer_work_queue(artifact_dir=tmp_path)


def test_no_answer_work_queue_rejects_promoted_source() -> None:
    source = copy.deepcopy(build_acontext_operator_activation_answer_schema_gate())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="source answer schema readiness promoted"):
        build_acontext_operator_activation_no_answer_work_queue(answer_schema_gate=source)

    source = copy.deepcopy(build_acontext_operator_activation_answer_schema_gate())
    source["current_answer_state"]["explicit_operator_answer_present"] = True

    with pytest.raises(CityOpsContractError, match="source records answer"):
        build_acontext_operator_activation_no_answer_work_queue(answer_schema_gate=source)
