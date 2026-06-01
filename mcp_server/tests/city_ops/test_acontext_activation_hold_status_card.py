"""Tests for the internal/admin Acontext activation hold status card."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from mcp_server.city_ops.acontext_activation_hold_status_card import (
    ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME,
    ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM,
    ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SCHEMA,
    ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_STOP_LINE,
    ACTIVATION_HOLD_STATUS_BLOCKED_CLAIMS,
    build_acontext_activation_hold_status_card,
    load_acontext_activation_hold_status_card,
    write_acontext_activation_hold_status_card,
)
from mcp_server.city_ops.acontext_multi_fixture_replay_gate import (
    ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME,
    ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM,
    build_acontext_multi_fixture_replay_gate,
)
from mcp_server.city_ops.contracts import CityOpsContractError


FIXTURES = Path(__file__).resolve().parents[2] / "city_ops" / "fixtures"
PROOF_BLOCK_DIR = FIXTURES / "proof_blocks" / "redirect_outdated_packet_001"


def _seed_sources(tmp_path: Path) -> None:
    for source in PROOF_BLOCK_DIR.glob("*.json"):
        if source.name == ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME:
            continue
        shutil.copy(source, tmp_path / source.name)
    assert (tmp_path / ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME).exists()


def test_activation_hold_status_card_matches_fixture() -> None:
    card = build_acontext_activation_hold_status_card()
    with (PROOF_BLOCK_DIR / ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME).open(
        "r", encoding="utf-8"
    ) as fh:
        fixture = json.load(fh)

    assert card == fixture
    assert load_acontext_activation_hold_status_card() == card
    assert card["schema"] == ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SCHEMA
    assert card["status_verdict"] == (
        "activation_hold_status_card_landed_default_hold_preserved_no_runtime_mutation"
    )
    assert ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM in card["claim_boundaries"][
        "safe_to_claim"
    ]
    assert ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM in card["claim_boundaries"][
        "safe_to_claim"
    ]


def test_activation_hold_status_records_no_answer_and_applies_default_hold() -> None:
    card = build_acontext_activation_hold_status_card()
    answer = card["operator_answer_state"]

    assert card["activation_candidate"]["candidate_id"] == "irc_session_manager_memory_sink"
    assert answer["explicit_operator_answer_present"] is False
    assert answer["operator_answer_value"] is None
    assert answer["operator_approval_record_present"] is False
    assert answer["current_decision"] == "hold_no_runtime_mutation"
    assert answer["this_card_is_not_an_approval_record"] is True
    assert card["hold_status"]["default_hold_preserved"] is True
    assert card["hold_status"]["activation_hold_status_card_landed"] is True


def test_activation_hold_status_keeps_runtime_and_external_surfaces_blocked() -> None:
    card = build_acontext_activation_hold_status_card()
    readiness = card["readiness"]

    assert readiness["safe_for_internal_admin_hold_status_display"] is True
    for key in [
        "safe_for_runtime_adapter_registration",
        "safe_for_runtime_adapter_enablement",
        "safe_for_runtime_session_manager_mutation",
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
    assert all(flag is False for flag in card["access_flags"].values())
    assert card["derived_from"]["starts_live_services"] is False
    assert card["derived_from"]["creates_sessions"] is False
    assert card["derived_from"]["writes_or_retrieves_messages"] is False


def test_activation_hold_status_references_may_31_replay_and_decision_context() -> None:
    card = build_acontext_activation_hold_status_card()
    source = card["source_artifacts"]["multi_fixture_replay_gate"]
    docs = card["source_artifacts"]["decision_context_docs"]

    assert source["file"] == ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME
    assert source["file_digest_sha256"] == (
        "bc45e1808e29360bcced6c106b48ec24c94fa8aeb91c35dfcf7aba63dd3b057f"
    )
    assert source["safe_claim"] == ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM
    assert [doc["file"] for doc in docs] == [
        "docs/planning/CITY_AS_A_SERVICE_ACONTEXT_OPERATOR_ACTIVATION_DECISION_REQUEST_2026_05_31.md",
        "docs/planning/CITY_AS_A_SERVICE_ACONTEXT_7AM_NO_MUTATION_ACTIVATION_HOLD_RUNBOOK_2026_05_31.md",
        "docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md",
    ]
    assert all(doc["records_approval"] is False for doc in docs)


def test_activation_hold_status_preserves_blocked_claim_boundaries() -> None:
    card = build_acontext_activation_hold_status_card()
    blocked = set(card["claim_boundaries"]["do_not_claim_yet"])
    safe = set(card["claim_boundaries"]["safe_to_claim"])

    assert set(ACTIVATION_HOLD_STATUS_BLOCKED_CLAIMS) <= blocked
    assert safe.isdisjoint(blocked)
    for required_fragment in [
        "records_operator_approval",
        "runtime_adapter_registration",
        "runtime_adapter_enablement",
        "irc_session_manager_mutation",
        "cross_project_autorouting",
        "customer_copy_delivery_or_publication",
        "public_or_catalog_route",
        "pricing_or_customer_quote",
        "queue_launch_or_dispatch",
        "erc8004_reputation",
        "worker_skill_dna",
        "payment_or_production",
        "exact_gps_or_raw_metadata",
        "private_operator_context",
        "domain_legal_emergency_repair_insurance_or_sla_authority",
        "worker_copyable_doctrine",
        "stopped_project_integration",
    ]:
        assert any(required_fragment in claim for claim in blocked)
        assert not any(required_fragment in claim for claim in safe)


def test_activation_hold_status_persists_no_secret_ids_payload_or_private_context() -> None:
    card = build_acontext_activation_hold_status_card()
    serialized = json.dumps(card).lower()

    assert "bearer " + "sk" + "-ac-" not in serialized
    assert "root_api" + "_bearer_token=" not in serialized
    assert "secret_key_" + "hmac" not in serialized
    assert "secret_key_" + "hash_phc" not in serialized
    assert re.search(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        serialized,
    ) is None
    assert "sanitized message" not in serialized
    assert "redacted_session_id" not in serialized
    assert "redacted_message_id" not in serialized


def test_activation_hold_status_stop_line_remains_fail_closed() -> None:
    card = build_acontext_activation_hold_status_card()

    assert card["operator_guidance"]["stop_line"] == ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_STOP_LINE
    assert "records no approval" in card["operator_guidance"]["stop_line"]
    assert "does not authorize runtime adapter registration" in card["operator_guidance"]["stop_line"]
    assert card["operator_guidance"]["not_customer_copy"] is True
    assert card["operator_guidance"]["not_worker_instruction"] is True
    assert card["operator_guidance"]["next_required_gate"] == (
        "separate_explicit_operator_answer_before_any_runtime_mutation"
    )


def test_activation_hold_status_write_and_load_round_trip(tmp_path: Path) -> None:
    _seed_sources(tmp_path)

    path = write_acontext_activation_hold_status_card(artifact_dir=tmp_path)

    assert path == tmp_path / ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME
    loaded = load_acontext_activation_hold_status_card(artifact_dir=tmp_path)
    assert loaded == build_acontext_activation_hold_status_card(artifact_dir=tmp_path)


def test_activation_hold_status_rejects_promoted_replay_source() -> None:
    source = copy.deepcopy(build_acontext_multi_fixture_replay_gate())
    source["readiness"]["safe_for_runtime_adapter_registration"] = True

    with pytest.raises(CityOpsContractError, match="source replay readiness promoted"):
        build_acontext_activation_hold_status_card(replay_gate=source)

    source = copy.deepcopy(build_acontext_multi_fixture_replay_gate())
    source["access_flags"]["dispatch_enabled"] = True

    with pytest.raises(CityOpsContractError, match="source replay access flag promoted"):
        build_acontext_activation_hold_status_card(replay_gate=source)


def test_activation_hold_status_loader_rejects_recorded_answer_or_runtime_promotion(
    tmp_path: Path,
) -> None:
    _seed_sources(tmp_path)
    path = write_acontext_activation_hold_status_card(artifact_dir=tmp_path)
    card = json.loads(path.read_text(encoding="utf-8"))
    card["operator_answer_state"]["explicit_operator_answer_present"] = True
    path.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="recorded operator answer"):
        load_acontext_activation_hold_status_card(artifact_dir=tmp_path)

    path = write_acontext_activation_hold_status_card(artifact_dir=tmp_path)
    card = json.loads(path.read_text(encoding="utf-8"))
    card["readiness"]["safe_for_runtime_adapter_enablement"] = True
    path.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(CityOpsContractError, match="readiness promoted"):
        load_acontext_activation_hold_status_card(artifact_dir=tmp_path)
