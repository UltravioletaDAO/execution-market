"""Internal/admin memory-to-Acontext readiness carry-forward card.

This proof block consumes the Acontext operator activation daytime handoff packet
and the coordination carry-forward matrix. It answers one narrow no-answer
question: if a future operator approves disabled/default-off design-only wiring,
which invariant fields must survive into that adapter contract?

It records no operator answer or approval, performs no live Acontext write or
retrieval, registers or enables no adapter, mutates no IRC/session-manager
runtime, creates no customer/public/worker surface, launches no queue or
dispatch, emits no ERC-8004 reputation or Worker Skill DNA signal, reverifies no
payment/production state, and exposes no exact GPS/raw metadata, private
operator context, raw transcripts, secrets, session IDs, or message IDs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .acontext_operator_activation_daytime_handoff_packet import (
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME,
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM,
    ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SCHEMA,
    DAYTIME_HANDOFF_BLOCKED_CLAIMS,
    load_acontext_operator_activation_daytime_handoff_packet,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SCHEMA = (
    "city_ops.aas_memory_acontext_readiness_carry_forward_card.v1"
)
AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME = (
    "aas_memory_acontext_readiness_carry_forward_card.json"
)
AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SAFE_CLAIM = (
    "internal_admin_aas_memory_acontext_readiness_carry_forward_card_landed"
)
AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_ID = (
    "execution_market.aas.memory_acontext_readiness_carry_forward_card.2026_06_02_0400"
)
AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_VERDICT = (
    "memory_acontext_readiness_carry_forward_card_landed_no_answer_runtime_hold_preserved"
)
COORDINATION_CARRY_FORWARD_MATRIX_FILENAME = (
    "docs/planning/CITY_AS_A_SERVICE_COORDINATION_CARRY_FORWARD_MATRIX.md"
)

CARRY_FORWARD_STOP_LINE = (
    "This card is an internal/admin readiness carry-forward only. It preserves "
    "the hold_no_runtime_mutation decision, records no answer or approval, and "
    "does not authorize Acontext writes or retrievals, adapter registration or "
    "enablement, IRC/session-manager mutation, cross-project autorouting, "
    "customer/public/worker exposure, pricing, queue, dispatch, reputation, "
    "Worker Skill DNA, payment/production claims, exact GPS/raw metadata release, "
    "private-context release, authority claims, worker-copyable doctrine, or "
    "stopped-project integration."
)

CARRY_FORWARD_BLOCKED_CLAIMS = [
    *DAYTIME_HANDOFF_BLOCKED_CLAIMS,
    "memory_acontext_card_records_operator_answer",
    "memory_acontext_card_records_operator_approval",
    "memory_acontext_card_selects_design_only_wiring",
    "memory_acontext_card_authorizes_bounded_activation_test",
    "memory_acontext_card_registers_runtime_adapter",
    "memory_acontext_card_enables_runtime_adapter",
    "memory_acontext_card_writes_live_acontext",
    "memory_acontext_card_retrieves_live_acontext",
    "memory_acontext_card_proves_runtime_parity",
    "memory_acontext_card_mutates_irc_session_manager",
    "memory_acontext_card_replays_raw_transcripts",
    "memory_acontext_card_ingests_private_operator_context",
    "memory_acontext_card_enables_cross_project_autorouting",
    "memory_acontext_card_creates_customer_copy_or_public_route",
    "memory_acontext_card_creates_worker_instruction_or_doctrine",
    "memory_acontext_card_authorizes_pricing_queue_or_dispatch",
    "memory_acontext_card_authorizes_erc8004_reputation_or_worker_skill_dna",
    "memory_acontext_card_reverifies_payment_or_production",
    "memory_acontext_card_allows_exact_gps_or_raw_metadata",
    "memory_acontext_card_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "memory_acontext_card_integrates_stopped_projects",
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
    re.compile(r"bearer\s+" r"sk" r"-[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"root_api" r"_bearer_token\s*=", re.IGNORECASE),
    re.compile(r"secret" r"_key_(?:hmac|hash_phc)", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE),
    re.compile(r"\b\S+@\S+\.\S+\b"),
    re.compile(r"\+?\d[\d\s().-]{2,}[\s().-]\d[\d\s().-]{4,}\d"),
]


def build_aas_memory_acontext_readiness_carry_forward_card(
    *,
    artifact_dir: str | Path | None = None,
    daytime_handoff_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin readiness carry-forward card."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = daytime_handoff_packet or load_acontext_operator_activation_daytime_handoff_packet(
        artifact_dir=base_dir
    )
    _assert_daytime_handoff_source_conservative(source)

    project_root = Path(__file__).resolve().parents[2]
    carry_forward_matrix = project_root / COORDINATION_CARRY_FORWARD_MATRIX_FILENAME
    if not carry_forward_matrix.exists():
        raise CityOpsContractError("coordination carry-forward matrix missing")

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM,
            AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *CARRY_FORWARD_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME
    card: dict[str, Any] = {
        "schema": AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SCHEMA,
        "card_id": AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_ID,
        "scope": "internal_admin_readiness_carry_forward_no_answer_no_approval_no_runtime_mutation",
        "status_verdict": AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_VERDICT,
        "source_artifacts": {
            "acontext_operator_activation_daytime_handoff_packet": {
                "file": ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME,
                "schema": source["schema"],
                "id": source["packet_id"],
                "safe_claim": ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": _file_digest(source_file),
                "status_verdict": source["status_verdict"],
            },
            "coordination_carry_forward_matrix": {
                "file": COORDINATION_CARRY_FORWARD_MATRIX_FILENAME,
                "digest_sha256": _file_digest(carry_forward_matrix),
                "source_role": "read_only_handoff_invariant_reference",
                "authorizes_runtime_action": False,
            },
        },
        "derived_from": {
            "read_only": True,
            "consumes_only": [
                ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME,
                COORDINATION_CARRY_FORWARD_MATRIX_FILENAME,
            ],
            "raw_transcripts_reopened": False,
            "raw_worker_evidence_reopened": False,
            "unreviewed_memory_reopened": False,
            "private_operator_context_reopened": False,
            "calls_acontext": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "changes_irc_runtime_session_manager": False,
            "enables_cross_project_autorouting": False,
            "writes_customer_copy": False,
            "writes_worker_instruction": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "reverifies_payment_or_production": False,
            "exposes_gps_or_metadata": False,
        },
        "activation_candidate": dict(source["activation_candidate"]),
        "readiness_carry_forward": {
            "card_landed": True,
            "current_decision": "hold_no_runtime_mutation",
            "effective_decision_after_card": "hold_no_runtime_mutation",
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "future_design_only_wiring_authorized_now": False,
            "future_bounded_activation_test_authorized_now": False,
            "adapter_registration_authorized_now": False,
            "adapter_enablement_authorized_now": False,
            "runtime_mutation_authorized_now": False,
            "answers_only": (
                "which invariant fields must survive into a future disabled/default-off "
                "adapter contract if a separate operator answer later approves design-only wiring"
            ),
        },
        "disabled_adapter_required_field_contract": _disabled_adapter_required_field_contract(),
        "field_survival_rules": _field_survival_rules(),
        "future_gate_order": [
            {
                "step": "explicit_operator_answer_record",
                "required_before": "any_approval_or_wiring",
                "passed_now": False,
            },
            {
                "step": "separate_design_only_wiring_approval_record",
                "required_before": "disabled_adapter_contract_implementation",
                "passed_now": False,
            },
            {
                "step": "default_off_adapter_contract_tests",
                "required_before": "adapter_registration_or_enablement",
                "passed_now": False,
            },
            {
                "step": "bounded_local_activation_test_approval_record",
                "required_before": "any_live_write_or_retrieval_attempt",
                "passed_now": False,
            },
        ],
        "stopped_project_firewall": dict(source["stopped_project_firewall"]),
        "access_flags": dict(_FALSE_ACCESS_FLAGS),
        "readiness": _readiness_flags(),
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "operator_guidance": {
            "stop_line": CARRY_FORWARD_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "next_required_gate": "separate_explicit_operator_answer_record_before_any_approval_wiring_or_activation_test",
            "if_no_human_answer": "use_this_card_only_as_internal_admin_field_contract_reference",
        },
    }
    _assert_card_conservative(card, source=source, source_file=source_file)
    return card


def write_aas_memory_acontext_readiness_carry_forward_card(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic readiness carry-forward card."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    card = build_aas_memory_acontext_readiness_carry_forward_card(artifact_dir=base_dir)
    path = base_dir / AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME
    path.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_memory_acontext_readiness_carry_forward_card(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted readiness carry-forward card."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME
    card = json.loads(path.read_text(encoding="utf-8"))
    source = load_acontext_operator_activation_daytime_handoff_packet(artifact_dir=base_dir)
    source_file = base_dir / ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_FILENAME
    _assert_card_conservative(card, source=source, source_file=source_file)
    if card != build_aas_memory_acontext_readiness_carry_forward_card(
        artifact_dir=base_dir,
        daytime_handoff_packet=source,
    ):
        raise CityOpsContractError("AAS memory-to-Acontext readiness carry-forward card fixture drift")
    return card


def _disabled_adapter_required_field_contract() -> list[dict[str, Any]]:
    return [
        {
            "field": "proof_anchor_id",
            "required": True,
            "purpose": "tie any future memory candidate back to a reviewed proof block",
            "source_class_allowed": "reviewed_internal_artifact_only",
            "may_contain_private_context": False,
        },
        {
            "field": "coordination_session_id_alias",
            "required": True,
            "purpose": "carry a sanitized alias rather than raw session or message identifiers",
            "source_class_allowed": "sanitized_handoff_alias_only",
            "may_contain_private_context": False,
        },
        {
            "field": "review_packet_id",
            "required": True,
            "purpose": "preserve the human-review surface that bounded the claim",
            "source_class_allowed": "reviewed_internal_artifact_only",
            "may_contain_private_context": False,
        },
        {
            "field": "compact_decision_id",
            "required": True,
            "purpose": "preserve the exact decision unit that explains why future dispatch guidance changed",
            "source_class_allowed": "reviewed_internal_artifact_only",
            "may_contain_private_context": False,
        },
        {
            "field": "source_artifact_digests",
            "required": True,
            "purpose": "make retrieved memory auditable without reopening raw transcripts or private context",
            "source_class_allowed": "sha256_digest_only",
            "may_contain_private_context": False,
        },
        {
            "field": "safe_to_claim",
            "required": True,
            "purpose": "keep allowed claims attached to the memory unit",
            "source_class_allowed": "claim_boundary_list",
            "may_contain_private_context": False,
        },
        {
            "field": "do_not_claim_yet",
            "required": True,
            "purpose": "keep sticky blocked claims attached to the memory unit",
            "source_class_allowed": "claim_boundary_list",
            "may_contain_private_context": False,
        },
        {
            "field": "next_required_gate",
            "required": True,
            "purpose": "prevent retrieved memory from masquerading as approval or runtime truth",
            "source_class_allowed": "operator_guidance_string",
            "may_contain_private_context": False,
        },
        {
            "field": "kill_switch_default",
            "required": True,
            "purpose": "force any future adapter contract to remain disabled until a separate approval record exists",
            "source_class_allowed": "literal_false_or_disabled",
            "may_contain_private_context": False,
        },
    ]


def _field_survival_rules() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "safe_and_blocked_claims_survive_together",
            "must_preserve": ["safe_to_claim", "do_not_claim_yet"],
            "failure_mode": "fail_closed_if_either_list_is_missing_or_overlaps",
        },
        {
            "rule_id": "invariant_ids_survive_without_raw_identifiers",
            "must_preserve": [
                "proof_anchor_id",
                "review_packet_id",
                "compact_decision_id",
                "coordination_session_id_alias",
            ],
            "failure_mode": "fail_closed_if_raw_session_ids_message_ids_or_private_context_are_present",
        },
        {
            "rule_id": "source_digests_survive_without_payload_replay",
            "must_preserve": ["source_artifact_digests"],
            "failure_mode": "fail_closed_if_adapter_attempts_to_reopen_raw_transcripts_or_unreviewed_memory",
        },
        {
            "rule_id": "approval_absence_survives_retrieval",
            "must_preserve": ["next_required_gate", "kill_switch_default"],
            "failure_mode": "fail_closed_if_retrieved_memory_changes_hold_no_runtime_mutation",
        },
    ]


def _readiness_flags() -> dict[str, bool]:
    return {
        "readiness_carry_forward_card_landed": True,
        "source_daytime_handoff_packet_validated": True,
        "coordination_carry_forward_matrix_referenced": True,
        "disabled_adapter_field_contract_named": True,
        "field_survival_rules_named": True,
        "operator_answer_absent": True,
        "operator_approval_record_absent": True,
        "default_hold_no_runtime_mutation_applied": True,
        "safe_for_internal_admin_field_contract_reference": True,
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
    }


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


def _assert_card_conservative(
    card: dict[str, Any], *, source: dict[str, Any], source_file: Path
) -> None:
    _assert_daytime_handoff_source_conservative(source)
    if card.get("schema") != AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SCHEMA:
        raise CityOpsContractError("unexpected memory-to-Acontext carry-forward card schema")
    if card.get("card_id") != AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_ID:
        raise CityOpsContractError("memory-to-Acontext carry-forward card id drift")
    if card.get("status_verdict") != AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_VERDICT:
        raise CityOpsContractError("memory-to-Acontext carry-forward card verdict drift")

    source_ref = card.get("source_artifacts", {}).get(
        "acontext_operator_activation_daytime_handoff_packet", {}
    )
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("memory-to-Acontext carry-forward source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(source_file):
        raise CityOpsContractError("memory-to-Acontext carry-forward source file digest drift")
    if source_ref.get("safe_claim") != ACONTEXT_OPERATOR_ACTIVATION_DAYTIME_HANDOFF_PACKET_SAFE_CLAIM:
        raise CityOpsContractError("memory-to-Acontext carry-forward source safe claim drift")

    carry = card.get("readiness_carry_forward", {})
    for key in [
        "card_landed",
    ]:
        if carry.get(key) is not True:
            raise CityOpsContractError(f"memory-to-Acontext carry-forward boundary missing: {key}")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "future_design_only_wiring_authorized_now",
        "future_bounded_activation_test_authorized_now",
        "adapter_registration_authorized_now",
        "adapter_enablement_authorized_now",
        "runtime_mutation_authorized_now",
    ]:
        if carry.get(key) is not False:
            raise CityOpsContractError(f"memory-to-Acontext carry-forward promoted: {key}")
    if carry.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("memory-to-Acontext carry-forward current decision drift")
    if carry.get("effective_decision_after_card") != "hold_no_runtime_mutation":
        raise CityOpsContractError("memory-to-Acontext carry-forward effective decision drift")

    required_fields = card.get("disabled_adapter_required_field_contract", [])
    required_names = {item.get("field") for item in required_fields if item.get("required") is True}
    for field in {
        "proof_anchor_id",
        "coordination_session_id_alias",
        "review_packet_id",
        "compact_decision_id",
        "source_artifact_digests",
        "safe_to_claim",
        "do_not_claim_yet",
        "next_required_gate",
        "kill_switch_default",
    }:
        if field not in required_names:
            raise CityOpsContractError(f"memory-to-Acontext carry-forward missing required adapter field: {field}")
    if any(item.get("may_contain_private_context") is not False for item in required_fields):
        raise CityOpsContractError("memory-to-Acontext carry-forward field permits private context")

    if not card.get("field_survival_rules"):
        raise CityOpsContractError("memory-to-Acontext carry-forward survival rules missing")
    if any(gate.get("passed_now") is not False for gate in card.get("future_gate_order", [])):
        raise CityOpsContractError("memory-to-Acontext carry-forward future gate already passed")

    for key, value in card.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"memory-to-Acontext carry-forward stopped project firewall promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if card.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"memory-to-Acontext carry-forward access flag promoted: {key}")

    readiness = card.get("readiness", {})
    for key in [
        "readiness_carry_forward_card_landed",
        "source_daytime_handoff_packet_validated",
        "coordination_carry_forward_matrix_referenced",
        "disabled_adapter_field_contract_named",
        "field_survival_rules_named",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_internal_admin_field_contract_reference",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"memory-to-Acontext carry-forward readiness missing: {key}")
    for key, value in readiness.items():
        if key not in {
            "readiness_carry_forward_card_landed",
            "source_daytime_handoff_packet_validated",
            "coordination_carry_forward_matrix_referenced",
            "disabled_adapter_field_contract_named",
            "field_survival_rules_named",
            "operator_answer_absent",
            "operator_approval_record_absent",
            "default_hold_no_runtime_mutation_applied",
            "safe_for_internal_admin_field_contract_reference",
        } and value is not False:
            raise CityOpsContractError(f"memory-to-Acontext carry-forward readiness promoted: {key}")

    _assert_claim_boundaries(
        card.get("claim_boundaries", {}).get("safe_to_claim", []),
        card.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SAFE_CLAIM not in card.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("memory-to-Acontext carry-forward missing safe claim")
    missing_blocked = set(CARRY_FORWARD_BLOCKED_CLAIMS) - set(
        card.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"memory-to-Acontext carry-forward missing blocked claims: {sorted(missing_blocked)}"
        )

    guidance = card.get("operator_guidance", {})
    if guidance.get("stop_line") != CARRY_FORWARD_STOP_LINE:
        raise CityOpsContractError("memory-to-Acontext carry-forward stop line drift")
    if guidance.get("not_customer_copy") is not True or guidance.get("not_worker_instruction") is not True:
        raise CityOpsContractError("memory-to-Acontext carry-forward external guidance drift")

    serialized = json.dumps(card, sort_keys=True).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("memory-to-Acontext carry-forward persisted secret, identifier, or PII pattern")


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
