"""Internal/admin Acontext operator activation daytime handoff packet.

This proof block consumes the read-only review packet and turns the 5 AM
synthesis into a daytime operator handoff: one current hold state, three
explicit human answer options, and fail-closed next actions.

It records no operator answer or approval, does not register or enable a
runtime adapter, does not mutate IRC/session-manager behavior, starts no
services, creates/writes/retrieves no Acontext records, exposes no customer,
public, or worker surface, launches no dispatch, emits no reputation, verifies
no payment/production claim, and persists no exact GPS/raw metadata, private
context, secrets, session IDs, or message IDs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_operator_activation_read_only_review_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SCHEMA,
    READ_ONLY_REVIEW_PACKET_BLOCKED_CLAIMS,
    load_acontext_operator_activation_read_only_review_packet,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SCHEMA = (
    "city_ops.acontext_operator_activation_daytime_handoff_packet.v1"
)
ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME = (
    "acontext_operator_activation_daytime_handoff_packet.json"
)
ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM = (
    "admin_acontext_operator_activation_daytime_handoff_packet_landed"
)
ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_ID = (
    "execution_market.aas.acontext_operator_activation_daytime_handoff_packet.2026_06_01_0500"
)
ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SCOPE = (
    "internal_admin_daytime_operator_handoff_no_answer_no_approval_no_runtime_mutation"
)
ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_VERDICT = (
    "daytime_handoff_packet_landed_current_hold_preserved_operator_answer_still_required"
)
ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_STOP_LINE = (
    "This packet is a daytime handoff only. It records no answer, records no "
    "approval, keeps the active decision at hold_no_runtime_mutation, and does "
    "not authorize design-only wiring, bounded activation tests, runtime adapter "
    "registration or enablement, IRC/session-manager mutation, cross-project "
    "autorouting, customer/public delivery, dispatch, reputation, payment/"
    "production claims, exact GPS/raw metadata release, private-context release, "
    "authority claims, worker-copyable doctrine, or stopped-project integration."
)

DAYTIME_HANDOFF_BLOCKED_CLAIMS = [
    *READ_ONLY_REVIEW_PACKET_BLOCKED_CLAIMS,
    "daytime_handoff_records_operator_answer",
    "daytime_handoff_records_operator_approval",
    "daytime_handoff_treats_handoff_as_approval",
    "daytime_handoff_changes_effective_decision",
    "daytime_handoff_selects_design_only_wiring",
    "daytime_handoff_selects_bounded_local_activation_test",
    "daytime_handoff_authorizes_runtime_adapter_registration",
    "daytime_handoff_authorizes_runtime_adapter_enablement",
    "daytime_handoff_authorizes_irc_session_manager_mutation",
    "daytime_handoff_authorizes_cross_project_autorouting",
    "daytime_handoff_authorizes_customer_copy_delivery_or_publication",
    "daytime_handoff_authorizes_queue_launch_or_dispatch",
    "daytime_handoff_authorizes_erc8004_reputation_or_worker_skill_dna",
    "daytime_handoff_reverifies_payment_or_production",
    "daytime_handoff_allows_exact_gps_or_raw_metadata",
    "daytime_handoff_releases_private_operator_context",
    "daytime_handoff_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "daytime_handoff_creates_worker_copyable_doctrine",
    "daytime_handoff_authorizes_stopped_project_integration",
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

_ALLOWED_OPERATOR_CHOICES = [
    {
        "choice_id": "hold_no_runtime_mutation",
        "meaning": "Keep the runtime-memory path paused; continue only read-only internal/admin review.",
        "separate_artifact_required": "separate_explicit_operator_answer_record_if_human_selects_this_choice",
        "runtime_mutation_authorized_by_choice_display": False,
    },
    {
        "choice_id": "approve_design_only_wiring_default_off",
        "meaning": "Permit only disabled design-only adapter wiring behind a kill switch; no live mutation.",
        "separate_artifact_required": "explicit_operator_answer_record_plus_separate_approval_record_before_any_wiring",
        "runtime_mutation_authorized_by_choice_display": False,
    },
    {
        "choice_id": "approve_one_bounded_local_activation_test",
        "meaning": "Permit exactly one bounded local activation test only after a separate approval record names scope, rollback, cleanup, and kill-switch requirements.",
        "separate_artifact_required": "explicit_operator_answer_record_plus_separate_approval_record_before_any_test",
        "runtime_mutation_authorized_by_choice_display": False,
    },
]

_SECRET_OR_IDENTIFIER_PATTERNS = [
    re.compile(r"bearer\s+" r"sk" r"-ac-[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"root_api" r"_bearer_token\s*=", re.IGNORECASE),
    re.compile(r"secret" r"_key_(?:hmac|hash_phc)", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE),
    re.compile(r"\b\S+@\S+\.\S+\b"),
    re.compile(r"\+?\d[\d\s().-]{2,}[\s().-]\d[\d\s().-]{4,}\d"),
]


def build_acontext_operator_activation_daytime_handoff_packet(
    *,
    artifact_dir: str | Path | None = None,
    read_only_review_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic daytime operator handoff packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = read_only_review_packet or load_acontext_operator_activation_read_only_review_packet(
        artifact_dir=base_dir
    )
    _assert_read_only_source_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM,
            ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *DAYTIME_HANDOFF_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME
    packet: dict[str, Any] = {
        "schema": ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SCHEMA,
        "packet_id": ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_ID,
        "scope": ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SCOPE,
        "status_verdict": ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_VERDICT,
        "source_artifacts": {
            "operator_activation_read_only_review_packet": {
                "file": ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME,
                "schema": source["schema"],
                "id": source["packet_id"],
                "safe_claim": ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": _file_digest(source_file),
                "status_verdict": source["status_verdict"],
            }
        },
        "activation_candidate": dict(source["activation_candidate"]),
        "daytime_handoff_packet": {
            "handoff_packet_id": "acontext_activation_daytime_operator_handoff_internal_admin_only",
            "intended_audience": "internal_admin_operator_only",
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "handoff_only_landed": True,
            "handoff_is_not_approval": True,
            "current_decision": "hold_no_runtime_mutation",
            "effective_decision_after_handoff": "hold_no_runtime_mutation",
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "records_customer_or_public_approval": False,
            "runtime_mutation_authorized": False,
            "bounded_activation_test_authorized": False,
            "daytime_focus": [
                "get_one_explicit_operator_answer_if_runtime_memory_continues",
                "otherwise_keep_default_hold_no_runtime_mutation",
                "do_not_mix_runtime_memory_with_customer_exposure_or_stopped_projects",
            ],
            "allowed_operator_choices_to_request": _ALLOWED_OPERATOR_CHOICES,
            "handoff_recommendation": {
                "recommended_default": "hold_no_runtime_mutation_until_explicit_human_answer",
                "recommended_next_if_human_answer_arrives": "create_separate_operator_answer_record_before_any_approval_or_wiring",
                "recommended_next_if_no_human_answer": "stop_or_continue_read_only_internal_admin_review_only",
                "product_exposure_fork": "separate_future_human_review_boundary_required_do_not_infer_from_runtime_memory",
            },
            "synthesis_connections": [
                {
                    "connection_id": "memory_system_to_acontext",
                    "safe_summary": "Durable memory can compound only when sanitized candidate data is digest-backed and promoted by an explicit operator answer chain.",
                    "action_authorized": "daytime_handoff_only",
                },
                {
                    "connection_id": "irc_coordination_to_claim_boundaries",
                    "safe_summary": "Agent coordination quality is the survival of safe-to-claim and do-not-claim-yet boundaries across handoffs.",
                    "action_authorized": "daytime_handoff_only",
                },
                {
                    "connection_id": "aas_portfolio_to_runtime_truth",
                    "safe_summary": "Runtime-memory activation and AAS customer exposure are separate forks; neither authorizes the other.",
                    "action_authorized": "daytime_handoff_only",
                },
            ],
        },
        "stopped_project_firewall": dict(source["stopped_project_firewall"]),
        "readiness": {
            "daytime_handoff_packet_landed": True,
            "source_read_only_review_packet_validated": True,
            "operator_answer_absent": True,
            "operator_approval_record_absent": True,
            "default_hold_no_runtime_mutation_applied": True,
            "safe_for_daytime_operator_handoff": True,
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
            "stop_line": ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "next_required_gate": "separate_explicit_operator_answer_record_before_any_approval_wiring_or_activation_test",
            "if_no_human_answer": "keep_default_hold_or_stop_at_daytime_handoff",
        },
    }
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    return packet


def write_acontext_operator_activation_daytime_handoff_packet(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic Acontext daytime handoff packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    packet = build_acontext_operator_activation_daytime_handoff_packet(artifact_dir=base_dir)
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_acontext_operator_activation_daytime_handoff_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted Acontext daytime handoff packet."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME
    packet = json.loads(path.read_text(encoding="utf-8"))
    source = load_acontext_operator_activation_read_only_review_packet(artifact_dir=base_dir)
    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_FILENAME
    _assert_packet_conservative(packet, source=source, source_file=source_file)
    if packet != build_acontext_operator_activation_daytime_handoff_packet(
        artifact_dir=base_dir,
        read_only_review_packet=source,
    ):
        raise CityOpsContractError("Acontext operator activation daytime handoff packet fixture drift")
    return packet


def _assert_read_only_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SCHEMA:
        raise CityOpsContractError("unexpected Acontext read-only review source schema")
    if ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext read-only review source safe claim missing")

    review = source.get("read_only_review_packet", {})
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if review.get(key) is not False:
            raise CityOpsContractError(f"source read-only review promoted: {key}")
    if review.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source read-only review current decision promoted")
    if review.get("effective_decision_after_review") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source read-only review effective decision promoted")
    if review.get("review_is_not_approval") is not True:
        raise CityOpsContractError("source read-only review approval boundary missing")

    readiness = source.get("readiness", {})
    for key in [
        "read_only_review_packet_landed",
        "source_answer_shape_validation_packet_validated",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_read_only_docs_fixture_review",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"source read-only review readiness missing: {key}")
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
            raise CityOpsContractError(f"source read-only review readiness promoted: {key}")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"source read-only review access flag promoted: {key}")
    for key, value in source.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"source read-only review stopped project firewall promoted: {key}")
    missing_blocked = set(READ_ONLY_REVIEW_PACKET_BLOCKED_CLAIMS) - set(
        source.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"source read-only review missing blocked claims: {sorted(missing_blocked)}"
        )


def _assert_packet_conservative(
    packet: dict[str, Any], *, source: dict[str, Any], source_file: Path
) -> None:
    _assert_read_only_source_conservative(source)
    if packet.get("schema") != ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SCHEMA:
        raise CityOpsContractError("unexpected Acontext daytime handoff packet schema")
    if packet.get("packet_id") != ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_ID:
        raise CityOpsContractError("Acontext daytime handoff packet id drift")
    if packet.get("status_verdict") != ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_VERDICT:
        raise CityOpsContractError("Acontext daytime handoff packet verdict drift")

    source_ref = packet.get("source_artifacts", {}).get("operator_activation_read_only_review_packet", {})
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("Acontext daytime handoff source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(source_file):
        raise CityOpsContractError("Acontext daytime handoff source file digest drift")
    if source_ref.get("safe_claim") != ACONTEXT_OPERATOR_ACTIVATION_READ_ONLY_REVIEW_PACKET_SAFE_CLAIM:
        raise CityOpsContractError("Acontext daytime handoff source safe claim drift")

    handoff = packet.get("daytime_handoff_packet", {})
    if handoff.get("intended_audience") != "internal_admin_operator_only":
        raise CityOpsContractError("Acontext daytime handoff audience drift")
    for key in ["not_customer_copy", "not_worker_instruction", "handoff_only_landed", "handoff_is_not_approval"]:
        if handoff.get(key) is not True:
            raise CityOpsContractError(f"Acontext daytime handoff boundary missing: {key}")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "records_customer_or_public_approval",
        "runtime_mutation_authorized",
        "bounded_activation_test_authorized",
    ]:
        if handoff.get(key) is not False:
            raise CityOpsContractError(f"Acontext daytime handoff promoted: {key}")
    if handoff.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext daytime handoff current decision drift")
    if handoff.get("effective_decision_after_handoff") != "hold_no_runtime_mutation":
        raise CityOpsContractError("Acontext daytime handoff effective decision drift")
    choices = handoff.get("allowed_operator_choices_to_request", [])
    if [item.get("choice_id") for item in choices] != [
        "hold_no_runtime_mutation",
        "approve_design_only_wiring_default_off",
        "approve_one_bounded_local_activation_test",
    ]:
        raise CityOpsContractError("Acontext daytime handoff choices drift")
    if any(item.get("runtime_mutation_authorized_by_choice_display") is not False for item in choices):
        raise CityOpsContractError("Acontext daytime handoff choice display authorized mutation")
    for item in handoff.get("synthesis_connections", []):
        if item.get("action_authorized") != "daytime_handoff_only":
            raise CityOpsContractError("Acontext daytime handoff synthesis authorized action")

    for key, value in packet.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"Acontext daytime handoff stopped project firewall promoted: {key}")

    readiness = packet.get("readiness", {})
    for key in [
        "daytime_handoff_packet_landed",
        "source_read_only_review_packet_validated",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_daytime_operator_handoff",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"Acontext daytime handoff readiness missing: {key}")
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
            raise CityOpsContractError(f"Acontext daytime handoff readiness promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if packet.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"Acontext daytime handoff access flag promoted: {key}")

    _assert_claim_boundaries(
        packet.get("claim_boundaries", {}).get("safe_to_claim", []),
        packet.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM not in packet.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("Acontext daytime handoff missing safe claim")

    serialized = json.dumps(packet, sort_keys=True).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("Acontext daytime handoff persisted secret, identifier, or PII pattern")


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
