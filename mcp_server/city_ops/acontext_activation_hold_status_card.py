"""Internal/admin Acontext activation hold status card.

This proof block consumes the May 31 Acontext multi-fixture replay gate and
operator decision context to make the current no-answer posture executable as a
deterministic artifact: absent an explicit operator answer, the runtime-memory
candidate remains in `hold_no_runtime_mutation`.

It deliberately records no approval, registers no runtime adapter, enables no
adapter, mutates no IRC/session-manager behavior, starts no services, creates no
sessions, writes or retrieves no messages, exposes no customer/worker/public
surface, launches no dispatch, emits no reputation, verifies no payment or
production claim, persists no exact GPS/raw metadata or private context, and
creates no worker-copyable doctrine.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_multi_fixture_replay_gate import (
    ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME,
    ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM,
    ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SCHEMA,
    MULTI_FIXTURE_REPLAY_BLOCKED_CLAIMS,
    load_acontext_multi_fixture_replay_gate,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SCHEMA = (
    "city_ops.acontext_activation_hold_status_card.v1"
)
ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME = (
    "acontext_activation_hold_status_card.json"
)
ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM = (
    "admin_acontext_activation_hold_status_card_landed"
)
ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_ID = (
    "execution_market.aas.acontext_activation_hold_status_card.2026_05_31_2205"
)
ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SCOPE = (
    "internal_admin_acontext_activation_hold_status_no_runtime_mutation"
)
ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_VERDICT = (
    "activation_hold_status_card_landed_default_hold_preserved_no_runtime_mutation"
)
ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_STOP_LINE = (
    "No explicit operator answer exists, so candidate irc_session_manager_memory_sink remains in "
    "hold_no_runtime_mutation. This status card records no approval and does not authorize runtime "
    "adapter registration, adapter enablement, IRC/session-manager mutation, cross-project "
    "autorouting, customer/public delivery, dispatch, reputation, payment/production claims, "
    "exact GPS/raw metadata release, private-context release, authority claims, worker-copyable "
    "doctrine, or stopped-project integration."
)

MAY_31_DECISION_CONTEXT_DOCS = [
    {
        "file": "docs/planning/CITY_AS_A_SERVICE_ACONTEXT_OPERATOR_ACTIVATION_DECISION_REQUEST_2026_05_31.md",
        "role": "names_required_operator_answer_before_runtime_mutation",
        "records_approval": False,
    },
    {
        "file": "docs/planning/CITY_AS_A_SERVICE_ACONTEXT_7AM_NO_MUTATION_ACTIVATION_HOLD_RUNBOOK_2026_05_31.md",
        "role": "states_absent_ambiguous_or_implied_answer_defaults_to_hold_no_runtime_mutation",
        "records_approval": False,
    },
    {
        "file": "docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md",
        "role": "daytime_internal_admin_handoff_board_preserving_hold_default",
        "records_approval": False,
    },
]

ACTIVATION_HOLD_STATUS_BLOCKED_CLAIMS = [
    *MULTI_FIXTURE_REPLAY_BLOCKED_CLAIMS,
    "activation_hold_status_card_records_operator_approval",
    "activation_hold_status_card_records_operator_answer",
    "activation_hold_status_card_selects_design_only_wiring",
    "activation_hold_status_card_selects_bounded_local_activation_test",
    "activation_hold_status_card_authorizes_runtime_adapter_registration",
    "activation_hold_status_card_authorizes_runtime_adapter_enablement",
    "activation_hold_status_card_authorizes_irc_session_manager_mutation",
    "activation_hold_status_card_authorizes_cross_project_autorouting",
    "activation_hold_status_card_authorizes_customer_copy_delivery_or_publication",
    "activation_hold_status_card_authorizes_public_or_catalog_route",
    "activation_hold_status_card_authorizes_pricing_or_customer_quote",
    "activation_hold_status_card_authorizes_queue_launch_or_dispatch",
    "activation_hold_status_card_authorizes_erc8004_reputation",
    "activation_hold_status_card_authorizes_worker_skill_dna",
    "activation_hold_status_card_reverifies_payment_or_production",
    "activation_hold_status_card_allows_exact_gps_or_raw_metadata",
    "activation_hold_status_card_releases_private_operator_context",
    "activation_hold_status_card_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "activation_hold_status_card_creates_worker_copyable_doctrine",
    "activation_hold_status_card_declares_general_acontext_sink_ready",
    "activation_hold_status_card_declares_runtime_parity_proven",
    "activation_hold_status_card_authorizes_stopped_project_integration",
]

_FALSE_ACCESS_FLAGS = {
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "irc_session_manager_mutated": False,
    "cross_project_autorouting_enabled": False,
    "network_route_registered": False,
    "public_route_registered": False,
    "catalog_route_registered": False,
    "customer_visible": False,
    "worker_visible": False,
    "pricing_enabled": False,
    "operator_queue_launched": False,
    "dispatch_enabled": False,
    "writes_live_acontext": False,
    "retrieves_live_acontext": False,
    "starts_live_services": False,
    "creates_sessions": False,
    "writes_messages": False,
    "retrieves_messages": False,
    "emits_reputation_receipts": False,
    "reverifies_payment_or_production": False,
    "exposes_gps_or_metadata": False,
    "releases_private_operator_context": False,
    "grants_domain_or_emergency_authority": False,
    "publishes_worker_doctrine": False,
    "integrates_stopped_projects": False,
}

_SECRET_OR_IDENTIFIER_PATTERNS = [
    re.compile(r"bearer\s+" r"sk" r"-ac-[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"root_api" r"_bearer_token\s*=", re.IGNORECASE),
    re.compile(r"secret_key_(?:hmac|hash_phc)", re.IGNORECASE),
    re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    ),
]


def build_acontext_activation_hold_status_card(
    *,
    artifact_dir: str | Path | None = None,
    replay_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic hold-status card for the no-answer activation posture."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = replay_gate or load_acontext_multi_fixture_replay_gate(artifact_dir=base_dir)
    _assert_replay_source_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM,
            ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *ACTIVATION_HOLD_STATUS_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    replay_file = base_dir / ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME
    card: dict[str, Any] = {
        "schema": ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SCHEMA,
        "card_id": ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_ID,
        "scope": ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SCOPE,
        "status_verdict": ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_VERDICT,
        "source_artifacts": {
            "multi_fixture_replay_gate": {
                "file": ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME,
                "schema": source["schema"],
                "id": source["gate_id"],
                "safe_claim": ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": _file_digest(replay_file),
                "gate_verdict": source["gate_verdict"],
            },
            "decision_context_docs": MAY_31_DECISION_CONTEXT_DOCS,
        },
        "derived_from": {
            "read_only_source_artifacts": True,
            "references_may_31_replay_and_decision_context": True,
            "operator_answer_absent": True,
            "default_decision_applied": "hold_no_runtime_mutation",
            "records_approval": False,
            "registers_runtime_adapter": False,
            "enables_runtime_adapter": False,
            "touches_irc_runtime_session_manager": False,
            "starts_live_services": False,
            "creates_sessions": False,
            "writes_or_retrieves_messages": False,
            "touches_customer_routes": False,
            "touches_worker_dispatch": False,
            "touches_reputation_payment_or_production": False,
            "touches_external_services": False,
        },
        "activation_candidate": {
            "candidate_id": "irc_session_manager_memory_sink",
            "latest_replay_safe_claim": ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM,
            "runtime_memory_default": "hold_no_runtime_mutation",
            "customer_or_worker_exposure": "none",
        },
        "operator_answer_state": {
            "explicit_operator_answer_present": False,
            "operator_answer_value": None,
            "operator_approval_record_present": False,
            "default_decision_when_absent_ambiguous_or_implied": "hold_no_runtime_mutation",
            "current_decision": "hold_no_runtime_mutation",
            "allowed_future_answers_require_separate_artifact": [
                "hold_no_runtime_mutation",
                "approve_design_only_wiring_default_off",
                "approve_one_bounded_local_activation_test",
            ],
            "this_card_is_not_an_approval_record": True,
        },
        "hold_status": {
            "activation_hold_status_card_landed": True,
            "default_hold_preserved": True,
            "runtime_adapter_registration_authorized": False,
            "runtime_adapter_enablement_authorized": False,
            "irc_session_manager_mutation_authorized": False,
            "bounded_local_activation_test_authorized": False,
            "customer_public_dispatch_reputation_payment_runtime_gps_private_context_authority_worker_doctrine_approved": False,
            "safe_admin_use": "show_internal_hold_status_until_separate_explicit_operator_answer_exists",
        },
        "readiness": {
            "activation_hold_status_card_landed": True,
            "source_multi_fixture_replay_gate_validated": True,
            "operator_answer_absent": True,
            "default_hold_no_runtime_mutation_applied": True,
            "safe_for_internal_admin_hold_status_display": True,
            "safe_for_runtime_adapter_registration": False,
            "safe_for_runtime_adapter_enablement": False,
            "safe_for_runtime_session_manager_mutation": False,
            "safe_for_cross_project_autorouting": False,
            "safe_for_customer_or_public_delivery": False,
            "safe_for_queue_launch_or_dispatch": False,
            "safe_for_reputation_or_worker_skill_dna": False,
            "safe_for_payment_or_production_claim": False,
            "safe_for_gps_or_raw_metadata_release": False,
            "safe_for_private_context_release": False,
            "safe_for_domain_legal_emergency_repair_insurance_or_sla_authority": False,
            "safe_for_worker_copyable_doctrine": False,
            "safe_for_stopped_project_integration": False,
            "general_acontext_sink_ready": False,
            "runtime_parity_proven": False,
            "operator_activation_approved": False,
        },
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_guidance": {
            "stop_line": ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "next_required_gate": "separate_explicit_operator_answer_before_any_runtime_mutation",
            "allowed_next_work_without_answer": [
                "display_this_internal_admin_hold_status_card",
                "continue_read_only_docs_or_fixture_review",
                "keep runtime customer dispatch reputation payment GPS private-context authority worker-doctrine and stopped-project claims blocked",
            ],
        },
    }
    _assert_card_conservative(card, source=source, replay_file=replay_file)
    return card


def write_acontext_activation_hold_status_card(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Acontext activation hold status card."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    card = build_acontext_activation_hold_status_card(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME
    path.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_activation_hold_status_card(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Acontext activation hold status card."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME
    card = json.loads(path.read_text(encoding="utf-8"))
    source = load_acontext_multi_fixture_replay_gate(artifact_dir=base_dir)
    replay_file = base_dir / ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_FILENAME
    _assert_card_conservative(card, source=source, replay_file=replay_file)
    if card != build_acontext_activation_hold_status_card(
        artifact_dir=base_dir,
        replay_gate=source,
    ):
        raise CityOpsContractError("Acontext activation hold status card fixture drift")
    return card


def _assert_replay_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SCHEMA:
        raise CityOpsContractError("unexpected Acontext multi-fixture replay source schema")
    if ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext multi-fixture replay source safe claim missing")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"source replay access flag promoted: {key}")
    for key in [
        "safe_for_runtime_adapter_registration",
        "safe_for_runtime_session_manager_mutation",
        "safe_for_cross_project_autorouting",
        "safe_for_customer_or_public_delivery",
        "safe_for_queue_launch_or_dispatch",
        "safe_for_reputation_or_worker_skill_dna",
        "safe_for_payment_or_production_claim",
        "safe_for_gps_or_raw_metadata_release",
        "safe_for_private_context_release",
        "safe_for_worker_copyable_doctrine",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
        "operator_activation_approved",
    ]:
        if source.get("readiness", {}).get(key) is not False:
            raise CityOpsContractError(f"source replay readiness promoted: {key}")
    missing_blocked = set(MULTI_FIXTURE_REPLAY_BLOCKED_CLAIMS) - set(
        source.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"source replay missing blocked claims: {sorted(missing_blocked)}"
        )


def _assert_card_conservative(
    card: dict[str, Any], *, source: dict[str, Any], replay_file: Path
) -> None:
    _assert_replay_source_conservative(source)
    if card.get("schema") != ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SCHEMA:
        raise CityOpsContractError("unexpected Acontext activation hold status card schema")
    if card.get("card_id") != ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_ID:
        raise CityOpsContractError("Acontext activation hold status card id drift")
    if card.get("scope") != ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SCOPE:
        raise CityOpsContractError("Acontext activation hold status card scope drift")
    if card.get("status_verdict") != ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_VERDICT:
        raise CityOpsContractError("Acontext activation hold status card verdict drift")

    source_ref = card.get("source_artifacts", {}).get("multi_fixture_replay_gate", {})
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("Acontext activation hold status source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(replay_file):
        raise CityOpsContractError("Acontext activation hold status source file digest drift")
    if source_ref.get("safe_claim") != ACONTEXT_MULTI_FIXTURE_REPLAY_GATE_SAFE_CLAIM:
        raise CityOpsContractError("Acontext activation hold status source safe claim drift")

    derived = card.get("derived_from", {})
    for key in [
        "read_only_source_artifacts",
        "references_may_31_replay_and_decision_context",
        "operator_answer_absent",
    ]:
        if derived.get(key) is not True:
            raise CityOpsContractError(f"Acontext activation hold status derived flag drift: {key}")
    for key in [
        "records_approval",
        "registers_runtime_adapter",
        "enables_runtime_adapter",
        "touches_irc_runtime_session_manager",
        "starts_live_services",
        "creates_sessions",
        "writes_or_retrieves_messages",
        "touches_customer_routes",
        "touches_worker_dispatch",
        "touches_reputation_payment_or_production",
        "touches_external_services",
    ]:
        if derived.get(key) is not False:
            raise CityOpsContractError(f"Acontext activation hold status derived promoted: {key}")

    answer = card.get("operator_answer_state", {})
    if answer.get("explicit_operator_answer_present") is not False:
        raise CityOpsContractError("Acontext activation hold status recorded operator answer")
    if answer.get("operator_answer_value") is not None:
        raise CityOpsContractError("Acontext activation hold status selected operator answer")
    if answer.get("operator_approval_record_present") is not False:
        raise CityOpsContractError("Acontext activation hold status recorded approval")
    if answer.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext activation hold status decision drift")
    if answer.get("this_card_is_not_an_approval_record") is not True:
        raise CityOpsContractError("Acontext activation hold status approval boundary drift")

    hold_status = card.get("hold_status", {})
    for key in [
        "runtime_adapter_registration_authorized",
        "runtime_adapter_enablement_authorized",
        "irc_session_manager_mutation_authorized",
        "bounded_local_activation_test_authorized",
        "customer_public_dispatch_reputation_payment_runtime_gps_private_context_authority_worker_doctrine_approved",
    ]:
        if hold_status.get(key) is not False:
            raise CityOpsContractError(f"Acontext activation hold status promoted: {key}")

    readiness = card.get("readiness", {})
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
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"Acontext activation hold status readiness promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if card.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"Acontext activation hold status access flag promoted: {key}")

    _assert_claim_boundaries(
        card.get("claim_boundaries", {}).get("safe_to_claim", []),
        card.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM not in card.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext activation hold status missing safe claim")
    if card.get("operator_guidance", {}).get("stop_line") != ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_STOP_LINE:
        raise CityOpsContractError("Acontext activation hold status stop line drift")

    serialized = json.dumps(card).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("Acontext activation hold status contains secret or identifier pattern")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"Acontext activation hold status claim overlap: {sorted(overlap)}")
    missing_blocked = set(ACTIVATION_HOLD_STATUS_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"Acontext activation hold status missing blocked claims: {sorted(missing_blocked)}"
        )


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
