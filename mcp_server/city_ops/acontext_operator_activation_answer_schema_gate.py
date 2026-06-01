"""Internal/admin Acontext operator activation answer schema gate.

This proof block consumes the Acontext activation hold status card and defines
how a *future* explicit operator answer must be shaped before any separate
runtime-memory activation artifact can even be considered.

It intentionally records no operator answer, records no approval, does not
register or enable a runtime adapter, does not mutate IRC/session-manager
behavior, does not start services, does not create/write/retrieve Acontext
sessions or messages, exposes no customer/public/worker surface, launches no
dispatch, emits no reputation, verifies no payment/production claim, and
persists no exact GPS/raw metadata, private context, secrets, session IDs, or
message IDs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_activation_hold_status_card import (
    ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME,
    ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM,
    ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SCHEMA,
    ACTIVATION_HOLD_STATUS_BLOCKED_CLAIMS,
    load_acontext_activation_hold_status_card,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SCHEMA = (
    "city_ops.acontext_operator_activation_answer_schema_gate.v1"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME = (
    "acontext_operator_activation_answer_schema_gate.json"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM = (
    "admin_acontext_operator_activation_answer_schema_gate_landed"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_ID = (
    "execution_market.aas.acontext_operator_activation_answer_schema_gate.2026_06_01_0000"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SCOPE = (
    "internal_admin_acontext_activation_answer_intake_schema_no_approval_recorded"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_VERDICT = (
    "answer_schema_gate_landed_no_operator_answer_recorded_default_hold_preserved"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_STOP_LINE = (
    "This gate only defines and validates the shape of a future explicit operator answer. "
    "It records no answer, records no approval, and does not authorize runtime adapter "
    "registration or enablement, IRC/session-manager mutation, bounded activation tests, "
    "customer/public delivery, dispatch, reputation, payment/production claims, exact "
    "GPS/raw metadata release, private-context release, authority claims, worker-copyable "
    "doctrine, or stopped-project integration."
)

ALLOWED_OPERATOR_ANSWER_VALUES = [
    "hold_no_runtime_mutation",
    "approve_design_only_wiring_default_off",
    "approve_one_bounded_local_activation_test",
]

ANSWER_SCHEMA_BLOCKED_CLAIMS = [
    *ACTIVATION_HOLD_STATUS_BLOCKED_CLAIMS,
    "answer_schema_gate_records_operator_answer",
    "answer_schema_gate_records_operator_approval",
    "answer_schema_gate_authorizes_runtime_adapter_registration",
    "answer_schema_gate_authorizes_runtime_adapter_enablement",
    "answer_schema_gate_authorizes_irc_session_manager_mutation",
    "answer_schema_gate_authorizes_bounded_activation_test_execution",
    "answer_schema_gate_authorizes_cross_project_autorouting",
    "answer_schema_gate_authorizes_customer_copy_delivery_or_publication",
    "answer_schema_gate_authorizes_public_or_catalog_route",
    "answer_schema_gate_authorizes_pricing_or_customer_quote",
    "answer_schema_gate_authorizes_queue_launch_or_dispatch",
    "answer_schema_gate_authorizes_erc8004_reputation",
    "answer_schema_gate_authorizes_worker_skill_dna",
    "answer_schema_gate_reverifies_payment_or_production",
    "answer_schema_gate_allows_exact_gps_or_raw_metadata",
    "answer_schema_gate_releases_private_operator_context",
    "answer_schema_gate_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "answer_schema_gate_creates_worker_copyable_doctrine",
    "answer_schema_gate_declares_general_acontext_sink_ready",
    "answer_schema_gate_declares_runtime_parity_proven",
    "answer_schema_gate_authorizes_stopped_project_integration",
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

_FORBIDDEN_ANSWER_PROMOTION_FLAGS = [
    "records_customer_or_public_approval",
    "authorizes_customer_or_public_delivery",
    "authorizes_runtime_adapter_registration",
    "authorizes_runtime_adapter_enablement",
    "authorizes_irc_session_manager_mutation",
    "authorizes_cross_project_autorouting",
    "authorizes_queue_launch_or_dispatch",
    "authorizes_reputation_or_worker_skill_dna",
    "authorizes_payment_or_production_claim",
    "allows_exact_gps_or_raw_metadata",
    "releases_private_context",
    "grants_domain_or_emergency_authority",
    "creates_worker_copyable_doctrine",
    "integrates_stopped_projects",
]

_SECRET_OR_IDENTIFIER_PATTERNS = [
    re.compile(r"bearer\s+" r"sk" r"-ac-[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"root_api" r"_bearer_token\s*=", re.IGNORECASE),
    re.compile(r"secret" r"_key_(?:hmac|hash_phc)", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE),
    re.compile(r"\b\S+@\S+\.\S+\b"),
    re.compile(r"\+?\d[\d\s().-]{7,}\d"),
]


def build_acontext_operator_activation_answer_schema_gate(
    *,
    artifact_dir: str | Path | None = None,
    hold_status_card: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic future-answer intake schema gate."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = hold_status_card or load_acontext_activation_hold_status_card(
        artifact_dir=base_dir
    )
    _assert_hold_status_source_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM,
            ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *ANSWER_SCHEMA_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME
    gate: dict[str, Any] = {
        "schema": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SCHEMA,
        "gate_id": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_ID,
        "scope": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SCOPE,
        "status_verdict": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_VERDICT,
        "source_artifacts": {
            "activation_hold_status_card": {
                "file": ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME,
                "schema": source["schema"],
                "id": source["card_id"],
                "safe_claim": ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": _file_digest(source_file),
                "status_verdict": source["status_verdict"],
            }
        },
        "activation_candidate": {
            "candidate_id": "irc_session_manager_memory_sink",
            "source_current_decision": source["operator_answer_state"]["current_decision"],
            "default_decision": "hold_no_runtime_mutation",
            "customer_or_worker_exposure": "none",
        },
        "current_answer_state": {
            "explicit_operator_answer_present": False,
            "operator_answer_value": None,
            "operator_approval_record_present": False,
            "answer_schema_validated": False,
            "validation_status": "not_evaluated_no_answer",
            "effective_decision": "hold_no_runtime_mutation",
            "this_gate_is_not_an_approval_record": True,
        },
        "answer_intake_contract": {
            "allowed_answer_values": ALLOWED_OPERATOR_ANSWER_VALUES,
            "shared_required_fields_for_any_future_answer": [
                "answer_value",
                "non_secret_operator_reference",
                "source_hold_status_card_file_digest_sha256",
                "preserve_all_blocked_claims",
                "records_customer_or_public_approval",
                "authorizes_runtime_adapter_registration",
                "authorizes_runtime_adapter_enablement",
                "authorizes_irc_session_manager_mutation",
                "authorizes_cross_project_autorouting",
                "authorizes_queue_launch_or_dispatch",
                "authorizes_reputation_or_worker_skill_dna",
                "authorizes_payment_or_production_claim",
                "allows_exact_gps_or_raw_metadata",
                "releases_private_context",
                "creates_worker_copyable_doctrine",
                "integrates_stopped_projects",
            ],
            "hold_no_runtime_mutation": {
                "records_approval": False,
                "keeps_default_hold": True,
                "requires_kill_switch": False,
                "requires_cleanup_quarantine_plan": False,
                "allows_runtime_mutation": False,
            },
            "approve_design_only_wiring_default_off": {
                "records_approval_in_this_gate": False,
                "requires_separate_approval_record": True,
                "requires_default_off_confirmation": True,
                "requires_kill_switch": True,
                "requires_rollback_plan": True,
                "requires_cleanup_quarantine_plan": True,
                "allows_live_session_manager_mutation_from_this_gate": False,
                "allows_activation_test_execution_from_this_gate": False,
            },
            "approve_one_bounded_local_activation_test": {
                "records_approval_in_this_gate": False,
                "requires_separate_approval_record": True,
                "requires_default_off_confirmation": True,
                "requires_kill_switch": True,
                "requires_rollback_plan": True,
                "requires_cleanup_quarantine_plan": True,
                "requires_sanitized_candidate_fixture_digest": True,
                "requires_local_only_one_attempt_limit": True,
                "allows_customer_public_dispatch_reputation_payment_or_production_from_this_gate": False,
            },
        },
        "readiness": {
            "answer_schema_gate_landed": True,
            "source_activation_hold_status_card_validated": True,
            "operator_answer_absent": True,
            "default_hold_no_runtime_mutation_applied": True,
            "safe_for_internal_admin_answer_intake_schema_display": True,
            "safe_for_runtime_adapter_registration": False,
            "safe_for_runtime_adapter_enablement": False,
            "safe_for_runtime_session_manager_mutation": False,
            "safe_for_bounded_activation_test_execution": False,
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
            "stop_line": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "next_required_gate": "separate_explicit_operator_answer_record_before_any_runtime_mutation_or_activation_test",
            "allowed_next_work_without_answer": [
                "display_this_internal_admin_answer_schema_gate",
                "validate_future_answer_shape_without_treating_it_as_approval",
                "continue_read_only_docs_or_fixture_review_while_preserving_all_blocked_claims",
            ],
        },
    }
    _assert_gate_conservative(gate, source=source, source_file=source_file)
    return gate


def validate_acontext_operator_activation_answer_shape(
    answer: dict[str, Any],
    *,
    expected_source_file_digest_sha256: str,
) -> dict[str, Any]:
    """Validate the shape of a future explicit operator answer.

    Passing this validator is deliberately **not** an approval and does not
    authorize runtime mutation; it only says a later separate approval artifact
    has enough non-secret fields to be reviewed.
    """

    if not isinstance(answer, dict):
        raise CityOpsContractError("operator answer must be a dictionary")
    serialized = json.dumps(answer, sort_keys=True).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("operator answer contains secret, identifier, or PII pattern")

    value = answer.get("answer_value")
    if value not in ALLOWED_OPERATOR_ANSWER_VALUES:
        raise CityOpsContractError("operator answer value not allowed")
    if answer.get("source_hold_status_card_file_digest_sha256") != expected_source_file_digest_sha256:
        raise CityOpsContractError("operator answer source digest mismatch")
    if not _safe_non_secret_reference(answer.get("non_secret_operator_reference")):
        raise CityOpsContractError("operator answer missing safe non-secret reference")
    if answer.get("preserve_all_blocked_claims") is not True:
        raise CityOpsContractError("operator answer does not preserve blocked claims")
    for flag in _FORBIDDEN_ANSWER_PROMOTION_FLAGS:
        if answer.get(flag) is not False:
            raise CityOpsContractError(f"operator answer promoted forbidden flag: {flag}")

    if value == "hold_no_runtime_mutation":
        _forbid_truthy(answer, [
            "default_off_confirmed",
            "kill_switch_required",
            "rollback_plan_required",
            "cleanup_quarantine_required",
            "sanitized_candidate_fixture_digest_sha256",
            "local_only_one_attempt_limit",
        ])
    elif value == "approve_design_only_wiring_default_off":
        _require_true(answer, [
            "default_off_confirmed",
            "kill_switch_required",
            "rollback_plan_required",
            "cleanup_quarantine_required",
        ])
        if answer.get("local_only_one_attempt_limit") is not False:
            raise CityOpsContractError("design-only wiring answer cannot request activation attempt")
        if answer.get("sanitized_candidate_fixture_digest_sha256") not in (None, ""):
            raise CityOpsContractError("design-only wiring answer cannot attach activation fixture digest")
    elif value == "approve_one_bounded_local_activation_test":
        _require_true(answer, [
            "default_off_confirmed",
            "kill_switch_required",
            "rollback_plan_required",
            "cleanup_quarantine_required",
            "local_only_one_attempt_limit",
        ])
        digest = answer.get("sanitized_candidate_fixture_digest_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise CityOpsContractError("bounded activation answer missing sanitized fixture digest")

    return {
        "valid_shape": True,
        "answer_value": value,
        "records_approval": False,
        "authorizes_runtime_mutation": False,
        "requires_separate_approval_artifact": value != "hold_no_runtime_mutation",
        "effective_decision_until_separate_artifact": "hold_no_runtime_mutation",
    }


def write_acontext_operator_activation_answer_schema_gate(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Acontext operator activation answer schema gate."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    gate = build_acontext_operator_activation_answer_schema_gate(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME
    path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_operator_activation_answer_schema_gate(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted answer schema gate."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_FILENAME
    gate = json.loads(path.read_text(encoding="utf-8"))
    source = load_acontext_activation_hold_status_card(artifact_dir=base_dir)
    source_file = base_dir / ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_FILENAME
    _assert_gate_conservative(gate, source=source, source_file=source_file)
    if gate != build_acontext_operator_activation_answer_schema_gate(
        artifact_dir=base_dir,
        hold_status_card=source,
    ):
        raise CityOpsContractError("Acontext operator activation answer schema gate fixture drift")
    return gate


def _assert_hold_status_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SCHEMA:
        raise CityOpsContractError("unexpected Acontext activation hold status source schema")
    if ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext activation hold source safe claim missing")
    if source.get("operator_answer_state", {}).get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext activation hold source decision promoted")
    if source.get("operator_answer_state", {}).get("explicit_operator_answer_present") is not False:
        raise CityOpsContractError("Acontext activation hold source records answer")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"source hold access flag promoted: {key}")
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
        "safe_for_worker_copyable_doctrine",
        "safe_for_stopped_project_integration",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
        "operator_activation_approved",
    ]:
        if source.get("readiness", {}).get(key) is not False:
            raise CityOpsContractError(f"source hold readiness promoted: {key}")
    missing_blocked = set(ACTIVATION_HOLD_STATUS_BLOCKED_CLAIMS) - set(
        source.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"source hold missing blocked claims: {sorted(missing_blocked)}"
        )


def _assert_gate_conservative(
    gate: dict[str, Any], *, source: dict[str, Any], source_file: Path
) -> None:
    _assert_hold_status_source_conservative(source)
    if gate.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SCHEMA:
        raise CityOpsContractError("unexpected Acontext answer schema gate schema")
    if gate.get("gate_id") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_ID:
        raise CityOpsContractError("Acontext answer schema gate id drift")
    if gate.get("scope") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SCOPE:
        raise CityOpsContractError("Acontext answer schema gate scope drift")
    if gate.get("status_verdict") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_VERDICT:
        raise CityOpsContractError("Acontext answer schema gate verdict drift")

    source_ref = gate.get("source_artifacts", {}).get("activation_hold_status_card", {})
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("Acontext answer schema source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(source_file):
        raise CityOpsContractError("Acontext answer schema source file digest drift")
    if source_ref.get("safe_claim") != ACONTEXT_ACTIVATION_HOLD_STATUS_CARD_SAFE_CLAIM:
        raise CityOpsContractError("Acontext answer schema source safe claim drift")

    state = gate.get("current_answer_state", {})
    if state.get("explicit_operator_answer_present") is not False:
        raise CityOpsContractError("Acontext answer schema gate recorded answer")
    if state.get("operator_answer_value") is not None:
        raise CityOpsContractError("Acontext answer schema gate selected answer")
    if state.get("operator_approval_record_present") is not False:
        raise CityOpsContractError("Acontext answer schema gate recorded approval")
    if state.get("effective_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext answer schema gate decision drift")
    if state.get("this_gate_is_not_an_approval_record") is not True:
        raise CityOpsContractError("Acontext answer schema approval boundary drift")

    if gate.get("answer_intake_contract", {}).get("allowed_answer_values") != ALLOWED_OPERATOR_ANSWER_VALUES:
        raise CityOpsContractError("Acontext answer schema allowed values drift")

    readiness = gate.get("readiness", {})
    if readiness.get("safe_for_internal_admin_answer_intake_schema_display") is not True:
        raise CityOpsContractError("Acontext answer schema display readiness missing")
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
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"Acontext answer schema readiness promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if gate.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"Acontext answer schema access flag promoted: {key}")

    _assert_claim_boundaries(
        gate.get("claim_boundaries", {}).get("safe_to_claim", []),
        gate.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_SAFE_CLAIM not in gate.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext answer schema missing safe claim")
    if gate.get("operator_guidance", {}).get("stop_line") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SCHEMA_GATE_STOP_LINE:
        raise CityOpsContractError("Acontext answer schema stop line drift")

    serialized = json.dumps(gate).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("Acontext answer schema contains secret, identifier, or PII pattern")


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"Acontext answer schema claim overlap: {sorted(overlap)}")
    missing_blocked = set(ANSWER_SCHEMA_BLOCKED_CLAIMS) - set(do_not_claim_yet)
    if missing_blocked:
        raise CityOpsContractError(
            f"Acontext answer schema missing blocked claims: {sorted(missing_blocked)}"
        )


def _safe_non_secret_reference(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not re.fullmatch(r"[a-z0-9_.:-]{8,96}", value):
        return False
    lower = value.lower()
    return not any(token in lower for token in ["@", "phone", "email", "address", "gps"])


def _require_true(answer: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        if answer.get(key) is not True:
            raise CityOpsContractError(f"operator answer missing required true flag: {key}")


def _forbid_truthy(answer: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        if answer.get(key) not in (False, None, ""):
            raise CityOpsContractError(f"hold answer included activation-only field: {key}")


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _stable_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
