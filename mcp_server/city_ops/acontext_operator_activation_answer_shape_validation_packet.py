"""Internal/admin Acontext operator activation answer-shape validation packet.

This proof block consumes the hold display packet and materializes only the
second allowed no-answer activity: validate the *shape contract* for future
operator answers.  It validates canned answer classes and rejection classes,
records no operator answer, records no approval, and keeps the effective
decision at ``hold_no_runtime_mutation``.

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
from .acontext_operator_activation_hold_display_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SCHEMA,
    HOLD_DISPLAY_PACKET_BLOCKED_CLAIMS,
    load_acontext_operator_activation_hold_display_packet,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SCHEMA = (
    "city_ops.acontext_operator_activation_answer_shape_validation_packet.v1"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME = (
    "acontext_operator_activation_answer_shape_validation_packet.json"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM = (
    "admin_acontext_operator_activation_answer_shape_validation_packet_landed"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_ID = (
    "execution_market.aas.acontext_operator_activation_answer_shape_validation_packet.2026_06_01_0300"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SCOPE = (
    "internal_admin_acontext_activation_future_answer_shape_validation_no_answer_no_approval"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_VERDICT = (
    "answer_shape_validation_packet_landed_no_answer_no_approval_default_hold_preserved"
)
ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_STOP_LINE = (
    "This packet validates only future operator answer shapes. It records no answer, "
    "records no approval, keeps the active decision at hold_no_runtime_mutation, and "
    "does not authorize runtime adapter registration or enablement, IRC/session-manager "
    "mutation, bounded activation tests, customer/public delivery, dispatch, reputation, "
    "payment/production claims, exact GPS/raw metadata release, private-context release, "
    "authority claims, worker-copyable doctrine, or stopped-project integration."
)

ANSWER_SHAPE_VALIDATION_PACKET_BLOCKED_CLAIMS = [
    *HOLD_DISPLAY_PACKET_BLOCKED_CLAIMS,
    "answer_shape_validation_packet_records_operator_answer",
    "answer_shape_validation_packet_records_operator_approval",
    "answer_shape_validation_packet_accepts_shape_validity_as_approval",
    "answer_shape_validation_packet_changes_effective_decision",
    "answer_shape_validation_packet_selects_design_only_wiring",
    "answer_shape_validation_packet_selects_bounded_local_activation_test",
    "answer_shape_validation_packet_authorizes_runtime_adapter_registration",
    "answer_shape_validation_packet_authorizes_runtime_adapter_enablement",
    "answer_shape_validation_packet_authorizes_irc_session_manager_mutation",
    "answer_shape_validation_packet_authorizes_bounded_activation_test_execution",
    "answer_shape_validation_packet_authorizes_cross_project_autorouting",
    "answer_shape_validation_packet_authorizes_customer_copy_delivery_or_publication",
    "answer_shape_validation_packet_authorizes_public_or_catalog_route",
    "answer_shape_validation_packet_authorizes_pricing_or_customer_quote",
    "answer_shape_validation_packet_authorizes_queue_launch_or_dispatch",
    "answer_shape_validation_packet_authorizes_erc8004_reputation",
    "answer_shape_validation_packet_authorizes_worker_skill_dna",
    "answer_shape_validation_packet_reverifies_payment_or_production",
    "answer_shape_validation_packet_allows_exact_gps_or_raw_metadata",
    "answer_shape_validation_packet_releases_private_operator_context",
    "answer_shape_validation_packet_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "answer_shape_validation_packet_creates_worker_copyable_doctrine",
    "answer_shape_validation_packet_declares_general_acontext_sink_ready",
    "answer_shape_validation_packet_declares_runtime_parity_proven",
    "answer_shape_validation_packet_authorizes_stopped_project_integration",
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

_VALIDATION_REQUIRED_FIELDS = [
    "answer_value",
    "non_secret_operator_reference",
    "source_hold_display_packet_file_digest_sha256",
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


def build_acontext_operator_activation_answer_shape_validation_packet(
    *,
    artifact_dir: str | Path | None = None,
    hold_display_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic future-answer shape validation packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = hold_display_packet or load_acontext_operator_activation_hold_display_packet(
        artifact_dir=base_dir
    )
    _assert_hold_display_source_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM,
            ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *ANSWER_SHAPE_VALIDATION_PACKET_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME
    source_digest = _file_digest(source_file)
    valid_examples = [
        _valid_answer_example(answer_value=value, source_digest=source_digest)
        for value in ALLOWED_OPERATOR_ANSWER_VALUES
    ]
    invalid_examples = [
        {
            "case_id": "reject_unrecognized_answer_value",
            "answer_value": "approve_live_runtime_mutation",
            "validation_status": "rejected",
            "rejection_reason": "answer_value_not_in_allowed_set",
        },
        {
            "case_id": "reject_missing_non_secret_operator_reference",
            "answer_value": "hold_no_runtime_mutation",
            "validation_status": "rejected",
            "rejection_reason": "missing_required_field_non_secret_operator_reference",
        },
        {
            "case_id": "reject_any_runtime_promotion_flag",
            "answer_value": "approve_design_only_wiring_default_off",
            "validation_status": "rejected",
            "rejection_reason": "promotion_flags_must_remain_false_in_shape_validation_packet",
        },
    ]

    packet: dict[str, Any] = {
        "schema": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SCHEMA,
        "packet_id": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_ID,
        "scope": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SCOPE,
        "status_verdict": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_VERDICT,
        "source_artifacts": {
            "operator_activation_hold_display_packet": {
                "file": ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME,
                "schema": source["schema"],
                "id": source["packet_id"],
                "safe_claim": ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": source_digest,
                "status_verdict": source["status_verdict"],
            }
        },
        "activation_candidate": dict(source["activation_candidate"]),
        "answer_shape_validation_packet": {
            "validation_packet_id": "acontext_activation_future_answer_shape_validator_internal_admin_only",
            "intended_audience": "internal_admin_operator_only",
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "current_decision": "hold_no_runtime_mutation",
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "records_customer_or_public_approval": False,
            "shape_validator_landed": True,
            "shape_validity_is_not_approval": True,
            "effective_decision_after_shape_validation": "hold_no_runtime_mutation",
            "runtime_mutation_authorized": False,
            "bounded_activation_test_authorized": False,
            "allowed_answer_values": ALLOWED_OPERATOR_ANSWER_VALUES,
            "required_fields_for_future_answer_shape": _VALIDATION_REQUIRED_FIELDS,
            "valid_shape_examples": valid_examples,
            "invalid_shape_examples": invalid_examples,
        },
        "stopped_project_firewall": dict(source["stopped_project_firewall"]),
        "readiness": {
            "answer_shape_validation_packet_landed": True,
            "source_hold_display_packet_validated": True,
            "operator_answer_absent": True,
            "operator_approval_record_absent": True,
            "default_hold_no_runtime_mutation_applied": True,
            "safe_for_future_answer_shape_validation": True,
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
            "stop_line": ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "next_required_gate": "separate_explicit_operator_answer_record_before_any_runtime_mutation_or_activation_test",
            "if_no_human_answer": "keep_default_hold_or_continue_read_only_internal_admin_docs_fixture_review_only",
        },
    }
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    return packet


def write_acontext_operator_activation_answer_shape_validation_packet(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Acontext future-answer shape validation packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    packet = build_acontext_operator_activation_answer_shape_validation_packet(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_operator_activation_answer_shape_validation_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Acontext future-answer shape validation packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_FILENAME
    packet = json.loads(path.read_text(encoding="utf-8"))
    source = load_acontext_operator_activation_hold_display_packet(artifact_dir=base_dir)
    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_FILENAME
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    if packet != build_acontext_operator_activation_answer_shape_validation_packet(
        artifact_dir=base_dir,
        hold_display_packet=source,
    ):
        raise CityOpsContractError("Acontext operator activation answer shape validation packet fixture drift")
    return packet


def _valid_answer_example(*, answer_value: str, source_digest: str) -> dict[str, Any]:
    return {
        "case_id": f"valid_shape_{answer_value}",
        "answer_value": answer_value,
        "non_secret_operator_reference": f"operator_decision_reference_for_{answer_value}",
        "source_hold_display_packet_file_digest_sha256": source_digest,
        "preserve_all_blocked_claims": True,
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
        "validation_status": "shape_valid_not_approval",
    }


def _assert_hold_display_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SCHEMA:
        raise CityOpsContractError("unexpected Acontext hold display packet source schema")
    if ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext hold display packet source safe claim missing")
    display = source.get("hold_display_packet", {})
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "answer_schema_validated",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if display.get(key) is not False:
            raise CityOpsContractError(f"source hold display promoted: {key}")
    if display.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source hold display decision promoted")
    if display.get("allowed_future_answer_values") != ALLOWED_OPERATOR_ANSWER_VALUES:
        raise CityOpsContractError("source hold display allowed answers drift")

    readiness = source.get("readiness", {})
    for key in [
        "hold_display_packet_landed",
        "source_no_answer_work_queue_validated",
        "operator_answer_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_internal_admin_hold_display",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"source hold display readiness missing: {key}")
    for key in [
        "safe_for_future_answer_validation",
        "safe_for_operator_answer_recording",
        "safe_for_operator_approval_recording",
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
        "safe_for_worker_copyable_doctrine",
        "safe_for_stopped_project_integration",
        "general_acontext_sink_ready",
        "runtime_parity_proven",
        "operator_activation_approved",
    ]:
        if readiness.get(key) is not False:
            raise CityOpsContractError(f"source hold display readiness promoted: {key}")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"source hold display access flag promoted: {key}")
    for key, value in source.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"source hold display stopped project firewall promoted: {key}")
    missing_blocked = set(HOLD_DISPLAY_PACKET_BLOCKED_CLAIMS) - set(
        source.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"source hold display missing blocked claims: {sorted(missing_blocked)}"
        )


def _assert_packet_conservative(
    packet: dict[str, Any], *, source: dict[str, Any], source_file: Path
) -> None:
    _assert_hold_display_source_conservative(source)
    if packet.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SCHEMA:
        raise CityOpsContractError("unexpected Acontext answer shape validation packet schema")
    if packet.get("packet_id") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_ID:
        raise CityOpsContractError("Acontext answer shape validation packet id drift")
    if packet.get("status_verdict") != ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_VERDICT:
        raise CityOpsContractError("Acontext answer shape validation packet verdict drift")

    source_ref = packet.get("source_artifacts", {}).get("operator_activation_hold_display_packet", {})
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("Acontext answer shape validation source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(source_file):
        raise CityOpsContractError("Acontext answer shape validation source file digest drift")
    if source_ref.get("safe_claim") != ACONTEXT_OPERATOR_ACTIVATION_HOLD_DISPLAY_PACKET_SAFE_CLAIM:
        raise CityOpsContractError("Acontext answer shape validation source safe claim drift")

    validation = packet.get("answer_shape_validation_packet", {})
    if validation.get("intended_audience") != "internal_admin_operator_only":
        raise CityOpsContractError("Acontext answer shape validation audience drift")
    for key in ["not_customer_copy", "not_worker_instruction", "shape_validator_landed", "shape_validity_is_not_approval"]:
        if validation.get(key) is not True:
            raise CityOpsContractError(f"Acontext answer shape validation boundary missing: {key}")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if validation.get(key) is not False:
            raise CityOpsContractError(f"Acontext answer shape validation promoted: {key}")
    if validation.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext answer shape validation current decision drift")
    if validation.get("effective_decision_after_shape_validation") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext answer shape validation effective decision drift")
    if validation.get("allowed_answer_values") != ALLOWED_OPERATOR_ANSWER_VALUES:
        raise CityOpsContractError("Acontext answer shape validation allowed answer values drift")
    if validation.get("required_fields_for_future_answer_shape") != _VALIDATION_REQUIRED_FIELDS:
        raise CityOpsContractError("Acontext answer shape validation required fields drift")

    valid_examples = validation.get("valid_shape_examples", [])
    if [item.get("answer_value") for item in valid_examples] != ALLOWED_OPERATOR_ANSWER_VALUES:
        raise CityOpsContractError("Acontext answer shape validation valid examples drift")
    for item in valid_examples:
        if item.get("validation_status") != "shape_valid_not_approval":
            raise CityOpsContractError("Acontext answer shape validation status drift")
        if item.get("preserve_all_blocked_claims") is not True:
            raise CityOpsContractError("Acontext answer shape validation blocked claim preservation missing")
        for key in _FORBIDDEN_PROMOTION_FLAGS:
            if item.get(key) is not False:
                raise CityOpsContractError(f"Acontext answer shape validation example promoted: {key}")
    invalid_examples = validation.get("invalid_shape_examples", [])
    if len(invalid_examples) != 3:
        raise CityOpsContractError("Acontext answer shape validation invalid examples drift")
    if any(item.get("validation_status") != "rejected" for item in invalid_examples):
        raise CityOpsContractError("Acontext answer shape validation invalid example accepted")

    for key, value in packet.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"Acontext answer shape validation stopped project firewall promoted: {key}")

    readiness = packet.get("readiness", {})
    for key in [
        "answer_shape_validation_packet_landed",
        "source_hold_display_packet_validated",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_future_answer_shape_validation",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"Acontext answer shape validation readiness missing: {key}")
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
            raise CityOpsContractError(f"Acontext answer shape validation readiness promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if packet.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"Acontext answer shape validation access flag promoted: {key}")

    _assert_claim_boundaries(
        packet.get("claim_boundaries", {}).get("safe_to_claim", []),
        packet.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if ACONTEXT_OPERATOR_ACTIVATION_ANSWER_SHAPE_VALIDATION_PACKET_SAFE_CLAIM not in packet.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext answer shape validation missing safe claim")

    serialized = json.dumps(packet, sort_keys=True).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("Acontext answer shape validation persisted secret, identifier, or PII pattern")


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
