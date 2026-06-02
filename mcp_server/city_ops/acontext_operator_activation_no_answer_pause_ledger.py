"""Internal/admin Acontext operator activation no-answer pause ledger.

This proof block consumes the answer-record dry-run validator and records the
current no-answer pause state as an internal/admin ledger.  It records no real
operator answer, records no approval, keeps the effective decision at
``hold_no_runtime_mutation``, and makes the absence of a human answer explicit
without turning any dry-run validation or displayed option into authority.

It does not register or enable a runtime adapter, does not mutate IRC/session-
manager behavior, does not start services, does not create/write/retrieve
Acontext sessions or messages, exposes no customer/public/worker surface,
launches no dispatch, emits no reputation, verifies no payment/production claim,
and persists no exact GPS/raw metadata, private context, secrets, session IDs,
or message IDs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_operator_activation_answer_record_dry_run_validator import (
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SCHEMA,
    ANSWER_RECORD_DRY_RUN_VALIDATOR_BLOCKED_CLAIMS,
    load_acontext_operator_activation_answer_record_dry_run_validator,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SCHEMA = (
    "city_ops.acontext_operator_activation_no_answer_pause_ledger.v1"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME = (
    "acontext_operator_activation_no_answer_pause_ledger.json"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SAFE_CLAIM = (
    "admin_acontext_operator_activation_no_answer_pause_ledger_landed"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_ID = (
    "execution_market.aas.acontext_operator_activation_no_answer_pause_ledger.2026_06_02_0100"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SCOPE = (
    "internal_admin_no_answer_pause_ledger_no_answer_no_approval_no_runtime_mutation"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_VERDICT = (
    "no_answer_pause_ledger_landed_hold_no_runtime_mutation_fail_closed"
)
ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_STOP_LINE = (
    "This ledger records only the current no-answer pause state. It records no "
    "operator answer, records no approval, keeps the active decision at "
    "hold_no_runtime_mutation, and does not authorize design-only wiring, "
    "bounded activation tests, runtime adapter registration or enablement, "
    "IRC/session-manager mutation, cross-project autorouting, customer/public "
    "delivery, dispatch, reputation, payment/production claims, exact GPS/raw "
    "metadata release, private-context release, authority claims, worker-copyable "
    "doctrine, or stopped-project integration."
)

NO_ANSWER_PAUSE_LEDGER_BLOCKED_CLAIMS = [
    *ANSWER_RECORD_DRY_RUN_VALIDATOR_BLOCKED_CLAIMS,
    "no_answer_pause_ledger_records_operator_answer",
    "no_answer_pause_ledger_records_operator_approval",
    "no_answer_pause_ledger_treats_pause_as_answer",
    "no_answer_pause_ledger_treats_pause_as_approval",
    "no_answer_pause_ledger_changes_effective_decision",
    "no_answer_pause_ledger_selects_design_only_wiring",
    "no_answer_pause_ledger_selects_bounded_local_activation_test",
    "no_answer_pause_ledger_authorizes_runtime_adapter_registration",
    "no_answer_pause_ledger_authorizes_runtime_adapter_enablement",
    "no_answer_pause_ledger_authorizes_irc_session_manager_mutation",
    "no_answer_pause_ledger_authorizes_bounded_activation_test_execution",
    "no_answer_pause_ledger_authorizes_cross_project_autorouting",
    "no_answer_pause_ledger_authorizes_customer_copy_delivery_or_publication",
    "no_answer_pause_ledger_authorizes_public_or_catalog_route",
    "no_answer_pause_ledger_authorizes_pricing_or_customer_quote",
    "no_answer_pause_ledger_authorizes_queue_launch_or_dispatch",
    "no_answer_pause_ledger_authorizes_erc8004_reputation",
    "no_answer_pause_ledger_authorizes_worker_skill_dna",
    "no_answer_pause_ledger_reverifies_payment_or_production",
    "no_answer_pause_ledger_allows_exact_gps_or_raw_metadata",
    "no_answer_pause_ledger_releases_private_operator_context",
    "no_answer_pause_ledger_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "no_answer_pause_ledger_creates_worker_copyable_doctrine",
    "no_answer_pause_ledger_declares_general_acontext_sink_ready",
    "no_answer_pause_ledger_declares_runtime_parity_proven",
    "no_answer_pause_ledger_authorizes_stopped_project_integration",
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
    re.compile(r"secret" r"_key_(?:hmac|hash_phc)", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE),
    re.compile(r"\b\S+@\S+\.\S+\b"),
    re.compile(r"\+?\d[\d\s().-]{2,}[\s().-]\d[\d\s().-]{4,}\d"),
]

_PAUSE_LEDGER_ENTRIES = [
    {
        "entry_id": "source_dry_run_validator_confirmed",
        "entry_type": "source_validation",
        "state": "dry_run_validator_present_but_not_answer_not_approval",
        "records_operator_answer": False,
        "records_operator_approval": False,
        "changes_effective_decision": False,
    },
    {
        "entry_id": "no_explicit_human_answer_present",
        "entry_type": "pause_reason",
        "state": "explicit_operator_answer_record_absent",
        "records_operator_answer": False,
        "records_operator_approval": False,
        "changes_effective_decision": False,
    },
    {
        "entry_id": "fail_closed_next_action",
        "entry_type": "operator_guidance",
        "state": "hold_or_wait_for_separate_explicit_answer_record",
        "records_operator_answer": False,
        "records_operator_approval": False,
        "changes_effective_decision": False,
    },
]


def build_acontext_operator_activation_no_answer_pause_ledger(
    *,
    artifact_dir: str | Path | None = None,
    dry_run_validator: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic internal/admin no-answer pause ledger."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = dry_run_validator or load_acontext_operator_activation_answer_record_dry_run_validator(
        artifact_dir=base_dir
    )
    _assert_dry_run_source_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SAFE_CLAIM,
            ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *NO_ANSWER_PAUSE_LEDGER_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME
    packet: dict[str, Any] = {
        "schema": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SCHEMA,
        "packet_id": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_ID,
        "scope": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SCOPE,
        "status_verdict": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_VERDICT,
        "source_artifacts": {
            "operator_activation_answer_record_dry_run_validator": {
                "file": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME,
                "schema": source["schema"],
                "id": source["packet_id"],
                "safe_claim": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": _file_digest(source_file),
                "status_verdict": source["status_verdict"],
            }
        },
        "activation_candidate": dict(source["activation_candidate"]),
        "no_answer_pause_ledger": {
            "ledger_id": "acontext_activation_no_answer_pause_internal_admin_only",
            "intended_audience": "internal_admin_operator_only",
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "ledger_landed": True,
            "ledger_is_not_answer_record": True,
            "ledger_is_not_approval": True,
            "source_dry_run_validator_validated": True,
            "current_decision": "hold_no_runtime_mutation",
            "effective_decision_after_pause": "hold_no_runtime_mutation",
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "records_customer_or_public_approval": False,
            "runtime_mutation_authorized": False,
            "bounded_activation_test_authorized": False,
            "pause_reason": "no_real_explicit_operator_answer_record_exists",
            "pause_entries": list(_PAUSE_LEDGER_ENTRIES),
            "fail_closed_blockers_carried_forward": list(
                source["answer_record_dry_run_validator"]["no_explicit_answer_fail_closed_blockers"]
            ),
            "eligible_future_actions_without_new_human_answer": [
                "keep_hold_no_runtime_mutation",
                "display_internal_admin_pause_state",
                "continue_read_only_docs_or_fixture_review_only",
            ],
            "only_unlocking_input": "separate_real_explicit_operator_answer_record_with_non_secret_reference",
            "forbidden_shortcuts": [
                "do_not_treat_dry_run_validator_as_answer",
                "do_not_treat_pause_ledger_as_answer",
                "do_not_treat_displayed_choice_as_approval",
                "do_not_select_design_only_wiring_without_separate_answer_and_approval_artifacts",
                "do_not_select_bounded_activation_test_without_separate_answer_and_approval_artifacts",
            ],
        },
        "stopped_project_firewall": dict(source["stopped_project_firewall"]),
        "readiness": {
            "no_answer_pause_ledger_landed": True,
            "source_answer_record_dry_run_validator_validated": True,
            "operator_answer_absent": True,
            "operator_approval_record_absent": True,
            "default_hold_no_runtime_mutation_applied": True,
            "safe_for_internal_admin_pause_display": True,
            "safe_for_read_only_docs_or_fixture_review": True,
            "safe_for_hypothetical_answer_record_dry_run_validation": True,
            "safe_for_operator_answer_recording": False,
            "safe_for_operator_approval_recording": False,
            "safe_for_design_only_wiring_selection": False,
            "safe_for_bounded_local_activation_test_selection": False,
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
            "stop_line": ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "recommended_default": "hold_no_runtime_mutation_until_real_explicit_human_answer_record_exists",
            "if_no_human_answer": "pause_or_continue_read_only_internal_admin_review_only",
            "if_human_answer_arrives": "create_separate_answer_record_artifact_then_separate_approval_artifact_if_needed",
        },
    }
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    return packet


def write_acontext_operator_activation_no_answer_pause_ledger(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Acontext no-answer pause ledger."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    packet = build_acontext_operator_activation_no_answer_pause_ledger(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_operator_activation_no_answer_pause_ledger(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Acontext no-answer pause ledger."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_FILENAME
    packet = json.loads(path.read_text(encoding="utf-8"))
    source = load_acontext_operator_activation_answer_record_dry_run_validator(artifact_dir=base_dir)
    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    if packet != build_acontext_operator_activation_no_answer_pause_ledger(
        artifact_dir=base_dir,
        dry_run_validator=source,
    ):
        raise CityOpsContractError("Acontext operator activation no-answer pause ledger fixture drift")
    return packet


def _assert_dry_run_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SCHEMA:
        raise CityOpsContractError("unexpected Acontext answer-record dry-run validator source schema")
    if ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext answer-record dry-run validator source safe claim missing")

    validator = source.get("answer_record_dry_run_validator", {})
    for key in [
        "not_customer_copy",
        "not_worker_instruction",
        "dry_run_only",
        "validator_landed",
        "validator_is_not_answer_record",
        "validator_is_not_approval",
    ]:
        if validator.get(key) is not True:
            raise CityOpsContractError(f"source dry-run validator boundary missing: {key}")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if validator.get(key) is not False:
            raise CityOpsContractError(f"source dry-run validator promoted: {key}")
    if validator.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source dry-run validator current decision promoted")
    if validator.get("effective_decision_after_dry_run") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source dry-run validator effective decision promoted")
    if not validator.get("no_explicit_answer_fail_closed_blockers"):
        raise CityOpsContractError("source dry-run validator missing no-answer blockers")

    readiness = source.get("readiness", {})
    for key in [
        "answer_record_dry_run_validator_landed",
        "source_daytime_handoff_packet_validated",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_hypothetical_answer_record_dry_run_validation",
        "no_explicit_answer_blockers_emitted",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"source dry-run validator readiness missing: {key}")
    for key in _PROMOTION_READINESS_FLAGS:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"source dry-run validator readiness promoted: {key}")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"source dry-run validator access flag promoted: {key}")
    for key, value in source.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"source dry-run validator stopped project firewall promoted: {key}")
    missing_blocked = set(ANSWER_RECORD_DRY_RUN_VALIDATOR_BLOCKED_CLAIMS) - set(
        source.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"source dry-run validator missing blocked claims: {sorted(missing_blocked)}"
        )


_PROMOTION_READINESS_FLAGS = [
    "safe_for_operator_answer_recording",
    "safe_for_operator_approval_recording",
    "safe_for_design_only_wiring_selection",
    "safe_for_bounded_local_activation_test_selection",
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
]


def _assert_packet_conservative(
    packet: dict[str, Any], *, source: dict[str, Any], source_file: Path
) -> None:
    _assert_dry_run_source_conservative(source)
    if packet.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SCHEMA:
        raise CityOpsContractError("unexpected Acontext no-answer pause ledger schema")
    if packet.get("packet_id") != ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_ID:
        raise CityOpsContractError("Acontext no-answer pause ledger id drift")
    if packet.get("status_verdict") != ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_VERDICT:
        raise CityOpsContractError("Acontext no-answer pause ledger verdict drift")

    source_ref = packet.get("source_artifacts", {}).get(
        "operator_activation_answer_record_dry_run_validator", {}
    )
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("Acontext no-answer pause ledger source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(source_file):
        raise CityOpsContractError("Acontext no-answer pause ledger source file digest drift")
    if source_ref.get("safe_claim") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SAFE_CLAIM:
        raise CityOpsContractError("Acontext no-answer pause ledger source safe claim drift")

    ledger = packet.get("no_answer_pause_ledger", {})
    if ledger.get("intended_audience") != "internal_admin_operator_only":
        raise CityOpsContractError("Acontext no-answer pause ledger audience drift")
    for key in [
        "not_customer_copy",
        "not_worker_instruction",
        "ledger_landed",
        "ledger_is_not_answer_record",
        "ledger_is_not_approval",
        "source_dry_run_validator_validated",
    ]:
        if ledger.get(key) is not True:
            raise CityOpsContractError(f"Acontext no-answer pause ledger boundary missing: {key}")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if ledger.get(key) is not False:
            raise CityOpsContractError(f"Acontext no-answer pause ledger promoted: {key}")
    if ledger.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext no-answer pause ledger current decision drift")
    if ledger.get("effective_decision_after_pause") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext no-answer pause ledger effective decision drift")
    if ledger.get("pause_reason") != "no_real_explicit_operator_answer_record_exists":
        raise CityOpsContractError("Acontext no-answer pause ledger pause reason drift")
    if ledger.get("pause_entries") != _PAUSE_LEDGER_ENTRIES:
        raise CityOpsContractError("Acontext no-answer pause ledger entries drift")
    for entry in ledger.get("pause_entries", []):
        for key in ["records_operator_answer", "records_operator_approval", "changes_effective_decision"]:
            if entry.get(key) is not False:
                raise CityOpsContractError(f"Acontext no-answer pause ledger entry promoted: {entry}")
    if ledger.get("fail_closed_blockers_carried_forward") != source.get(
        "answer_record_dry_run_validator", {}
    ).get("no_explicit_answer_fail_closed_blockers"):
        raise CityOpsContractError("Acontext no-answer pause ledger blocker carry-forward drift")
    if ledger.get("only_unlocking_input") != "separate_real_explicit_operator_answer_record_with_non_secret_reference":
        raise CityOpsContractError("Acontext no-answer pause ledger unlocking input drift")

    for key, value in packet.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"Acontext no-answer pause ledger stopped project firewall promoted: {key}")

    readiness = packet.get("readiness", {})
    for key in [
        "no_answer_pause_ledger_landed",
        "source_answer_record_dry_run_validator_validated",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_internal_admin_pause_display",
        "safe_for_read_only_docs_or_fixture_review",
        "safe_for_hypothetical_answer_record_dry_run_validation",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"Acontext no-answer pause ledger readiness missing: {key}")
    for key in _PROMOTION_READINESS_FLAGS:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"Acontext no-answer pause ledger readiness promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if packet.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"Acontext no-answer pause ledger access flag promoted: {key}")

    _assert_claim_boundaries(
        packet.get("claim_boundaries", {}).get("safe_to_claim", []),
        packet.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_SAFE_CLAIM not in packet.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext no-answer pause ledger missing safe claim")

    guidance = packet.get("operator_guidance", {})
    if guidance.get("stop_line") != ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_STOP_LINE:
        raise CityOpsContractError("Acontext no-answer pause ledger stop line drift")
    if guidance.get("not_customer_copy") is not True or guidance.get("not_worker_instruction") is not True:
        raise CityOpsContractError("Acontext no-answer pause ledger guidance exposure drift")

    serialized = json.dumps(packet, sort_keys=True).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError(
                "Acontext no-answer pause ledger persisted secret, identifier, or PII pattern"
            )


def _assert_claim_boundaries(safe_to_claim: list[str], do_not_claim_yet: list[str]) -> None:
    if not safe_to_claim or not do_not_claim_yet:
        raise CityOpsContractError("claim boundaries must be explicit")
    overlap = set(safe_to_claim) & set(do_not_claim_yet)
    if overlap:
        raise CityOpsContractError(f"claim boundary overlap: {sorted(overlap)}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
