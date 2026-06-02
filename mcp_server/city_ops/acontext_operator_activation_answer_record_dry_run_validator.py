"""Internal/admin Acontext operator activation answer-record dry-run validator.

This proof block consumes the daytime handoff packet and validates only
hypothetical future operator answer records.  It produces fail-closed blockers
when no explicit answer exists, records no operator answer, records no approval,
and keeps the effective decision at ``hold_no_runtime_mutation``.

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

from .acontext_operator_activation_answer_schema_gate import ALLOWED_OPERATOR_ANSWER_VALUES
from .acontext_operator_activation_daytime_handoff_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SCHEMA,
    DAYTIME_HANDOFF_BLOCKED_CLAIMS,
    load_acontext_operator_activation_daytime_handoff_packet,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SCHEMA = (
    "city_ops.acontext_operator_activation_answer_record_dry_run_validator.v1"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME = (
    "acontext_operator_activation_answer_record_dry_run_validator.json"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SAFE_CLAIM = (
    "admin_acontext_operator_activation_answer_record_dry_run_validator_landed"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_ID = (
    "execution_market.aas.acontext_operator_activation_answer_record_dry_run_validator.2026_06_01_2200"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SCOPE = (
    "internal_admin_hypothetical_answer_record_dry_run_no_answer_no_approval_no_runtime_mutation"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_VERDICT = (
    "answer_record_dry_run_validator_landed_no_explicit_answer_blockers_fail_closed"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_STOP_LINE = (
    "This packet validates only hypothetical answer-record candidates. It records "
    "no real operator answer, records no approval, keeps the active decision at "
    "hold_no_runtime_mutation, treats no-answer as fail-closed, and does not "
    "authorize design-only wiring, bounded activation tests, runtime adapter "
    "registration or enablement, IRC/session-manager mutation, cross-project "
    "autorouting, customer/public delivery, dispatch, reputation, payment/"
    "production claims, exact GPS/raw metadata release, private-context release, "
    "authority claims, worker-copyable doctrine, or stopped-project integration."
)

ANSWER_RECORD_DRY_RUN_VALIDATOR_BLOCKED_CLAIMS = [
    *DAYTIME_HANDOFF_BLOCKED_CLAIMS,
    "answer_record_dry_run_validator_records_operator_answer",
    "answer_record_dry_run_validator_records_operator_approval",
    "answer_record_dry_run_validator_treats_dry_run_as_answer",
    "answer_record_dry_run_validator_treats_validation_as_approval",
    "answer_record_dry_run_validator_changes_effective_decision",
    "answer_record_dry_run_validator_selects_design_only_wiring",
    "answer_record_dry_run_validator_selects_bounded_local_activation_test",
    "answer_record_dry_run_validator_authorizes_runtime_adapter_registration",
    "answer_record_dry_run_validator_authorizes_runtime_adapter_enablement",
    "answer_record_dry_run_validator_authorizes_irc_session_manager_mutation",
    "answer_record_dry_run_validator_authorizes_bounded_activation_test_execution",
    "answer_record_dry_run_validator_authorizes_cross_project_autorouting",
    "answer_record_dry_run_validator_authorizes_customer_copy_delivery_or_publication",
    "answer_record_dry_run_validator_authorizes_public_or_catalog_route",
    "answer_record_dry_run_validator_authorizes_pricing_or_customer_quote",
    "answer_record_dry_run_validator_authorizes_queue_launch_or_dispatch",
    "answer_record_dry_run_validator_authorizes_erc8004_reputation",
    "answer_record_dry_run_validator_authorizes_worker_skill_dna",
    "answer_record_dry_run_validator_reverifies_payment_or_production",
    "answer_record_dry_run_validator_allows_exact_gps_or_raw_metadata",
    "answer_record_dry_run_validator_releases_private_operator_context",
    "answer_record_dry_run_validator_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "answer_record_dry_run_validator_creates_worker_copyable_doctrine",
    "answer_record_dry_run_validator_declares_general_acontext_sink_ready",
    "answer_record_dry_run_validator_declares_runtime_parity_proven",
    "answer_record_dry_run_validator_authorizes_stopped_project_integration",
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

_REQUIRED_HYPOTHETICAL_RECORD_FIELDS = [
    "answer_value",
    "non_secret_operator_reference",
    "source_daytime_handoff_packet_file_digest_sha256",
    "answer_is_explicit_human_statement",
    "dry_run_only",
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
]

_FORBIDDEN_PROMOTION_FLAGS = [
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
]


def build_acontext_operator_activation_answer_record_dry_run_validator(
    *,
    artifact_dir: str | Path | None = None,
    daytime_handoff_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic hypothetical answer-record dry-run validator."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = daytime_handoff_packet or load_acontext_operator_activation_daytime_handoff_packet(
        artifact_dir=base_dir
    )
    _assert_daytime_handoff_source_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM,
            ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *ANSWER_RECORD_DRY_RUN_VALIDATOR_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME
    source_digest = _file_digest(source_file)
    valid_dry_run_records = [
        _hypothetical_answer_record(answer_value=value, source_digest=source_digest)
        for value in ALLOWED_OPERATOR_ANSWER_VALUES
    ]
    rejected_dry_run_records = [
        {
            "case_id": "reject_no_explicit_answer_record_present",
            "validation_status": "rejected_fail_closed",
            "rejection_reason": "missing_explicit_operator_answer_record",
            "fail_closed_blockers": [
                "no_explicit_operator_answer_record_present",
                "no_non_secret_human_reference_present",
                "keep_effective_decision_hold_no_runtime_mutation",
            ],
        },
        {
            "case_id": "reject_unrecognized_answer_value",
            "answer_value": "approve_live_runtime_mutation",
            "validation_status": "rejected_fail_closed",
            "rejection_reason": "answer_value_not_in_allowed_set",
        },
        {
            "case_id": "reject_source_digest_mismatch",
            "answer_value": "hold_no_runtime_mutation",
            "validation_status": "rejected_fail_closed",
            "rejection_reason": "source_daytime_handoff_packet_digest_mismatch",
        },
        {
            "case_id": "reject_any_runtime_or_public_promotion_flag",
            "answer_value": "approve_design_only_wiring_default_off",
            "validation_status": "rejected_fail_closed",
            "rejection_reason": "promotion_flags_must_remain_false_for_dry_run_validation",
        },
    ]

    packet: dict[str, Any] = {
        "schema": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SCHEMA,
        "packet_id": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_ID,
        "scope": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SCOPE,
        "status_verdict": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_VERDICT,
        "source_artifacts": {
            "operator_activation_daytime_handoff_packet": {
                "file": ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME,
                "schema": source["schema"],
                "id": source["packet_id"],
                "safe_claim": ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": source_digest,
                "status_verdict": source["status_verdict"],
            }
        },
        "activation_candidate": dict(source["activation_candidate"]),
        "answer_record_dry_run_validator": {
            "validator_id": "acontext_activation_hypothetical_answer_record_dry_run_internal_admin_only",
            "intended_audience": "internal_admin_operator_only",
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "dry_run_only": True,
            "validator_landed": True,
            "validator_is_not_answer_record": True,
            "validator_is_not_approval": True,
            "current_decision": "hold_no_runtime_mutation",
            "effective_decision_after_dry_run": "hold_no_runtime_mutation",
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "records_customer_or_public_approval": False,
            "runtime_mutation_authorized": False,
            "bounded_activation_test_authorized": False,
            "allowed_answer_values": list(ALLOWED_OPERATOR_ANSWER_VALUES),
            "required_hypothetical_record_fields": list(_REQUIRED_HYPOTHETICAL_RECORD_FIELDS),
            "forbidden_promotion_flags": list(_FORBIDDEN_PROMOTION_FLAGS),
            "valid_hypothetical_answer_records": valid_dry_run_records,
            "rejected_hypothetical_answer_records": rejected_dry_run_records,
            "no_explicit_answer_fail_closed_blockers": [
                "explicit_operator_answer_record_absent",
                "operator_approval_record_absent",
                "do_not_select_design_only_wiring",
                "do_not_select_bounded_local_activation_test",
                "do_not_register_or_enable_runtime_adapter",
                "do_not_mutate_irc_session_manager",
                "do_not_expose_customer_public_worker_or_catalog_surface",
            ],
            "validator_recommendation": {
                "recommended_default": "hold_no_runtime_mutation_until_real_explicit_human_answer_record_exists",
                "if_real_answer_arrives": "validate_again_then_create_separate_answer_record_artifact_without_treating_it_as_approval",
                "if_no_real_answer": "stop_or_continue_read_only_internal_admin_review_only",
            },
        },
        "stopped_project_firewall": dict(source["stopped_project_firewall"]),
        "readiness": {
            "answer_record_dry_run_validator_landed": True,
            "source_daytime_handoff_packet_validated": True,
            "operator_answer_absent": True,
            "operator_approval_record_absent": True,
            "default_hold_no_runtime_mutation_applied": True,
            "safe_for_hypothetical_answer_record_dry_run_validation": True,
            "no_explicit_answer_blockers_emitted": True,
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
            "stop_line": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "next_required_gate": "real_explicit_operator_answer_record_if_human_answer_exists_otherwise_hold",
            "if_no_human_answer": "fail_closed_keep_default_hold_no_runtime_mutation",
        },
    }
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    return packet


def write_acontext_operator_activation_answer_record_dry_run_validator(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Acontext answer-record dry-run validator."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    packet = build_acontext_operator_activation_answer_record_dry_run_validator(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_operator_activation_answer_record_dry_run_validator(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Acontext answer-record dry-run validator."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_FILENAME
    packet = json.loads(path.read_text(encoding="utf-8"))
    source = load_acontext_operator_activation_daytime_handoff_packet(artifact_dir=base_dir)
    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    if packet != build_acontext_operator_activation_answer_record_dry_run_validator(
        artifact_dir=base_dir,
        daytime_handoff_packet=source,
    ):
        raise CityOpsContractError(
            "Acontext operator activation answer-record dry-run validator fixture drift"
        )
    return packet


def _assert_daytime_handoff_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SCHEMA:
        raise CityOpsContractError("unexpected Acontext daytime handoff source schema")
    if ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext daytime handoff source safe claim missing")

    handoff = source.get("daytime_handoff_packet", {})
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if handoff.get(key) is not False:
            raise CityOpsContractError(f"source daytime handoff promoted: {key}")
    if handoff.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source daytime handoff current decision promoted")
    if handoff.get("effective_decision_after_handoff") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source daytime handoff effective decision promoted")
    if handoff.get("handoff_is_not_approval") is not True:
        raise CityOpsContractError("source daytime handoff approval boundary missing")

    readiness = source.get("readiness", {})
    for key in [
        "daytime_handoff_packet_landed",
        "source_read_only_review_packet_validated",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_daytime_operator_handoff",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"source daytime handoff readiness missing: {key}")
    for key in [
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
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"source daytime handoff readiness promoted: {key}")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"source daytime handoff access flag promoted: {key}")
    for key, value in source.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"source daytime handoff stopped project firewall promoted: {key}")
    missing_blocked = set(DAYTIME_HANDOFF_BLOCKED_CLAIMS) - set(
        source.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"source daytime handoff missing blocked claims: {sorted(missing_blocked)}"
        )


def _assert_packet_conservative(
    packet: dict[str, Any], *, source: dict[str, Any], source_file: Path
) -> None:
    _assert_daytime_handoff_source_conservative(source)
    if packet.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SCHEMA:
        raise CityOpsContractError("unexpected Acontext answer-record dry-run validator schema")
    if packet.get("packet_id") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_ID:
        raise CityOpsContractError("Acontext answer-record dry-run validator id drift")
    if packet.get("status_verdict") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_VERDICT:
        raise CityOpsContractError("Acontext answer-record dry-run validator verdict drift")

    source_ref = packet.get("source_artifacts", {}).get("operator_activation_daytime_handoff_packet", {})
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("Acontext answer-record dry-run validator source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(source_file):
        raise CityOpsContractError("Acontext answer-record dry-run validator source file digest drift")
    if source_ref.get("safe_claim") != ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM:
        raise CityOpsContractError("Acontext answer-record dry-run validator source safe claim drift")

    validator = packet.get("answer_record_dry_run_validator", {})
    if validator.get("intended_audience") != "internal_admin_operator_only":
        raise CityOpsContractError("Acontext answer-record dry-run validator audience drift")
    for key in [
        "not_customer_copy",
        "not_worker_instruction",
        "dry_run_only",
        "validator_landed",
        "validator_is_not_answer_record",
        "validator_is_not_approval",
    ]:
        if validator.get(key) is not True:
            raise CityOpsContractError(f"Acontext answer-record dry-run validator boundary missing: {key}")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if validator.get(key) is not False:
            raise CityOpsContractError(f"Acontext answer-record dry-run validator promoted: {key}")
    if validator.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext answer-record dry-run validator current decision drift")
    if validator.get("effective_decision_after_dry_run") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext answer-record dry-run validator effective decision drift")
    if validator.get("allowed_answer_values") != ALLOWED_OPERATOR_ANSWER_VALUES:
        raise CityOpsContractError("Acontext answer-record dry-run validator allowed values drift")
    if validator.get("required_hypothetical_record_fields") != _REQUIRED_HYPOTHETICAL_RECORD_FIELDS:
        raise CityOpsContractError("Acontext answer-record dry-run validator required fields drift")
    if validator.get("forbidden_promotion_flags") != _FORBIDDEN_PROMOTION_FLAGS:
        raise CityOpsContractError("Acontext answer-record dry-run validator promotion flags drift")
    if [item.get("answer_value") for item in validator.get("valid_hypothetical_answer_records", [])] != list(
        ALLOWED_OPERATOR_ANSWER_VALUES
    ):
        raise CityOpsContractError("Acontext answer-record dry-run validator valid records drift")
    for item in validator.get("valid_hypothetical_answer_records", []):
        if item.get("validation_status") != "hypothetical_record_valid_not_answer_not_approval":
            raise CityOpsContractError("Acontext answer-record dry-run validator treated valid dry run as answer")
        _assert_hypothetical_answer_record(item, expected_source_digest=_file_digest(source_file))
    rejected_cases = {item.get("case_id") for item in validator.get("rejected_hypothetical_answer_records", [])}
    if rejected_cases != {
        "reject_no_explicit_answer_record_present",
        "reject_unrecognized_answer_value",
        "reject_source_digest_mismatch",
        "reject_any_runtime_or_public_promotion_flag",
    }:
        raise CityOpsContractError("Acontext answer-record dry-run validator rejection cases drift")
    if not validator.get("no_explicit_answer_fail_closed_blockers"):
        raise CityOpsContractError("Acontext answer-record dry-run validator missing no-answer blockers")

    for key, value in packet.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"Acontext answer-record dry-run validator stopped project firewall promoted: {key}")

    readiness = packet.get("readiness", {})
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
            raise CityOpsContractError(f"Acontext answer-record dry-run validator readiness missing: {key}")
    for key in [
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
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"Acontext answer-record dry-run validator readiness promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if packet.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"Acontext answer-record dry-run validator access flag promoted: {key}")

    _assert_claim_boundaries(
        packet.get("claim_boundaries", {}).get("safe_to_claim", []),
        packet.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_SAFE_CLAIM not in packet.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext answer-record dry-run validator missing safe claim")

    guidance = packet.get("operator_guidance", {})
    if guidance.get("stop_line") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_STOP_LINE:
        raise CityOpsContractError("Acontext answer-record dry-run validator stop line drift")
    if guidance.get("not_customer_copy") is not True or guidance.get("not_worker_instruction") is not True:
        raise CityOpsContractError("Acontext answer-record dry-run validator guidance exposure drift")

    serialized = json.dumps(packet, sort_keys=True).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError(
                "Acontext answer-record dry-run validator persisted secret, identifier, or PII pattern"
            )


def _hypothetical_answer_record(*, answer_value: str, source_digest: str) -> dict[str, Any]:
    return {
        "case_id": f"valid_hypothetical_{answer_value}",
        "answer_value": answer_value,
        "non_secret_operator_reference": "operator_reference_required_at_real_answer_time",
        "source_daytime_handoff_packet_file_digest_sha256": source_digest,
        "answer_is_explicit_human_statement": True,
        "dry_run_only": True,
        "preserve_all_blocked_claims": True,
        "validation_status": "hypothetical_record_valid_not_answer_not_approval",
        "records_customer_or_public_approval": False,
        "authorizes_runtime_adapter_registration": False,
        "authorizes_runtime_adapter_enablement": False,
        "authorizes_irc_session_manager_mutation": False,
        "authorizes_cross_project_autorouting": False,
        "authorizes_queue_launch_or_dispatch": False,
        "authorizes_reputation_or_worker_skill_dna": False,
        "authorizes_payment_or_production_claim": False,
        "allows_exact_gps_or_raw_metadata": False,
        "releases_private_context": False,
        "creates_worker_copyable_doctrine": False,
        "integrates_stopped_projects": False,
    }


def _assert_hypothetical_answer_record(record: dict[str, Any], *, expected_source_digest: str) -> None:
    missing = [key for key in _REQUIRED_HYPOTHETICAL_RECORD_FIELDS if key not in record]
    if missing:
        raise CityOpsContractError(f"hypothetical answer record missing required fields: {missing}")
    if record.get("answer_value") not in ALLOWED_OPERATOR_ANSWER_VALUES:
        raise CityOpsContractError("hypothetical answer record answer value not allowed")
    if not record.get("non_secret_operator_reference"):
        raise CityOpsContractError("hypothetical answer record missing non-secret operator reference")
    if record.get("source_daytime_handoff_packet_file_digest_sha256") != expected_source_digest:
        raise CityOpsContractError("hypothetical answer record source digest mismatch")
    if record.get("answer_is_explicit_human_statement") is not True:
        raise CityOpsContractError("hypothetical answer record explicit human statement missing")
    if record.get("dry_run_only") is not True:
        raise CityOpsContractError("hypothetical answer record dry-run flag missing")
    if record.get("preserve_all_blocked_claims") is not True:
        raise CityOpsContractError("hypothetical answer record blocked claims not preserved")
    for key in _FORBIDDEN_PROMOTION_FLAGS:
        if record.get(key) is not False:
            raise CityOpsContractError(f"hypothetical answer record promotion flag set: {key}")


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
