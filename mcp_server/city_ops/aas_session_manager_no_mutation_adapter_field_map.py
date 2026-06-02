"""Internal/admin no-mutation session-manager adapter field map.

This proof block consumes the memory-to-Acontext readiness carry-forward card
and answers one narrow no-answer question: if a future operator separately
approves disabled/default-off design-only wiring, which fields may enter an IRC
session-manager adapter shape, and which fields must remain excluded forever?

It records no operator answer or approval, registers or enables no adapter,
mutates no IRC/session-manager runtime, calls no Acontext service, writes or
retrieves no live memory, creates no customer/public/worker surface, launches no
queue or dispatch, emits no ERC-8004 reputation or Worker Skill DNA signal,
reverifies no payment/production state, and exposes no exact GPS/raw metadata,
private operator context, raw transcripts, secrets, session IDs, or message IDs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .aas_memory_acontext_readiness_carry_forward_card import (
    AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME,
    AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SAFE_CLAIM,
    AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SCHEMA,
    CARRY_FORWARD_BLOCKED_CLAIMS,
    load_aas_memory_acontext_readiness_carry_forward_card,
)
from .contracts import CityOpsContractError
from .proof_block_artifacts import _default_proof_block_dir

AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SCHEMA = (
    "city_ops.aas_session_manager_no_mutation_adapter_field_map.v1"
)
AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME = (
    "aas_session_manager_no_mutation_adapter_field_map.json"
)
AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM = (
    "internal_admin_aas_session_manager_no_mutation_adapter_field_map_landed"
)
AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_ID = (
    "execution_market.aas.session_manager_no_mutation_adapter_field_map.2026_06_02_0500"
)
AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_VERDICT = (
    "session_manager_no_mutation_adapter_field_map_landed_no_answer_runtime_hold_preserved"
)

SESSION_MANAGER_FIELD_MAP_STOP_LINE = (
    "This field map is an internal/admin no-mutation adapter shape only. It "
    "records no answer or approval, preserves hold_no_runtime_mutation, and "
    "does not authorize IRC/session-manager mutation, adapter registration or "
    "enablement, Acontext writes or retrievals, cross-project autorouting, "
    "customer/public/worker exposure, pricing, queue, dispatch, reputation, "
    "Worker Skill DNA, payment/production claims, exact GPS/raw metadata release, "
    "private-context release, authority claims, worker-copyable doctrine, or "
    "stopped-project integration."
)

SESSION_MANAGER_FIELD_MAP_BLOCKED_CLAIMS = [
    *CARRY_FORWARD_BLOCKED_CLAIMS,
    "session_manager_field_map_records_operator_answer",
    "session_manager_field_map_records_operator_approval",
    "session_manager_field_map_selects_design_only_wiring",
    "session_manager_field_map_authorizes_bounded_activation_test",
    "session_manager_field_map_registers_adapter",
    "session_manager_field_map_enables_adapter",
    "session_manager_field_map_mutates_session_manager",
    "session_manager_field_map_writes_live_acontext",
    "session_manager_field_map_retrieves_live_acontext",
    "session_manager_field_map_proves_runtime_parity",
    "session_manager_field_map_replays_raw_transcripts",
    "session_manager_field_map_persists_raw_session_or_message_ids",
    "session_manager_field_map_ingests_private_operator_context",
    "session_manager_field_map_enables_cross_project_autorouting",
    "session_manager_field_map_creates_customer_public_or_worker_surface",
    "session_manager_field_map_creates_worker_instruction_or_doctrine",
    "session_manager_field_map_authorizes_pricing_queue_or_dispatch",
    "session_manager_field_map_authorizes_erc8004_reputation_or_worker_skill_dna",
    "session_manager_field_map_reverifies_payment_or_production",
    "session_manager_field_map_allows_exact_gps_or_raw_metadata",
    "session_manager_field_map_grants_domain_legal_emergency_repair_insurance_or_sla_authority",
    "session_manager_field_map_integrates_stopped_projects",
]

_FALSE_ACCESS_FLAGS = {
    "adapter_shape_documented": True,
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "session_manager_mutated": False,
    "session_manager_config_written": False,
    "session_manager_route_registered": False,
    "acontext_write_enabled": False,
    "acontext_retrieval_enabled": False,
    "cross_project_autorouting_enabled": False,
    "customer_visible": False,
    "public_visible": False,
    "worker_visible": False,
    "pricing_enabled": False,
    "operator_queue_launched": False,
    "dispatch_enabled": False,
    "reputation_emission_enabled": False,
    "payment_or_production_reverified": False,
    "gps_or_raw_metadata_exposed": False,
    "private_context_released": False,
    "authority_claim_granted": False,
    "worker_doctrine_published": False,
    "stopped_projects_integrated": False,
}

_SECRET_OR_IDENTIFIER_PATTERNS = [
    re.compile(r"bearer\s+" r"sk" r"-[a-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"root_api" r"_bearer_token\s*=", re.IGNORECASE),
    re.compile(r"secret" r"_key_(?:hmac|hash_phc)", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE),
    re.compile(r"\b\S+@\S+\.\S+\b"),
    re.compile(r"\+?\d[\d\s().-]{2,}[\s().-]\d[\d\s().-]{4,}\d"),
]


def build_aas_session_manager_no_mutation_adapter_field_map(
    *,
    artifact_dir: str | Path | None = None,
    carry_forward_card: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic internal/admin no-mutation field map."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    source = carry_forward_card or load_aas_memory_acontext_readiness_carry_forward_card(
        artifact_dir=base_dir
    )
    _assert_carry_forward_source_conservative(source)

    safe_to_claim = _dedupe(
        [
            *source["claim_boundaries"]["safe_to_claim"],
            AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SAFE_CLAIM,
            AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *source["claim_boundaries"]["do_not_claim_yet"],
            *SESSION_MANAGER_FIELD_MAP_BLOCKED_CLAIMS,
        ]
    )
    _assert_claim_boundaries(safe_to_claim, do_not_claim_yet)

    source_file = base_dir / AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME
    field_map: dict[str, Any] = {
        "schema": AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SCHEMA,
        "field_map_id": AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_ID,
        "scope": "internal_admin_session_manager_adapter_shape_no_answer_no_approval_no_runtime_mutation",
        "status_verdict": AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_VERDICT,
        "source_artifacts": {
            "memory_acontext_readiness_carry_forward_card": {
                "file": AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME,
                "schema": source["schema"],
                "id": source["card_id"],
                "safe_claim": AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SAFE_CLAIM,
                "canonical_digest_sha256": _stable_digest(source),
                "file_digest_sha256": _file_digest(source_file),
                "status_verdict": source["status_verdict"],
            }
        },
        "derived_from": {
            "read_only": True,
            "consumes_only": [AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME],
            "raw_transcripts_reopened": False,
            "raw_session_ids_reopened": False,
            "raw_message_ids_reopened": False,
            "raw_worker_evidence_reopened": False,
            "private_operator_context_reopened": False,
            "calls_acontext": False,
            "writes_live_acontext": False,
            "retrieves_live_acontext": False,
            "changes_irc_runtime_session_manager": False,
            "writes_session_manager_config": False,
            "registers_adapter": False,
            "enables_adapter": False,
            "enables_cross_project_autorouting": False,
            "writes_customer_copy": False,
            "writes_worker_instruction": False,
            "enables_dispatch_automation": False,
            "emits_reputation_receipts": False,
            "reverifies_payment_or_production": False,
            "exposes_gps_or_metadata": False,
        },
        "activation_candidate": dict(source["activation_candidate"]),
        "no_mutation_adapter_field_map": {
            "field_map_landed": True,
            "current_decision": "hold_no_runtime_mutation",
            "effective_decision_after_field_map": "hold_no_runtime_mutation",
            "explicit_operator_answer_present": False,
            "operator_approval_record_present": False,
            "design_only_wiring_authorized_now": False,
            "bounded_activation_test_authorized_now": False,
            "adapter_registration_authorized_now": False,
            "adapter_enablement_authorized_now": False,
            "session_manager_mutation_authorized_now": False,
            "answers_only": (
                "which carry-forward fields may enter a future disabled/default-off "
                "IRC session-manager adapter shape, and which fields must stay excluded"
            ),
        },
        "allowed_adapter_fields": _allowed_adapter_fields(source),
        "excluded_fields_forever": _excluded_fields_forever(),
        "adapter_runtime_defaults": _adapter_runtime_defaults(),
        "future_gate_order": [
            {
                "step": "explicit_operator_answer_record",
                "required_before": "any_approval_wiring_or_adapter_registration",
                "passed_now": False,
            },
            {
                "step": "separate_design_only_wiring_approval_record",
                "required_before": "disabled_session_manager_adapter_contract_implementation",
                "passed_now": False,
            },
            {
                "step": "no_mutation_adapter_contract_tests",
                "required_before": "any_session_manager_config_write",
                "passed_now": False,
            },
            {
                "step": "bounded_local_activation_test_approval_record",
                "required_before": "any_live_session_manager_or_acontext_attempt",
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
            "stop_line": SESSION_MANAGER_FIELD_MAP_STOP_LINE,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "next_required_gate": "separate_explicit_operator_answer_record_before_any_session_manager_wiring_or_activation_test",
            "if_no_human_answer": "use_this_map_only_as_internal_admin_adapter_shape_reference",
        },
    }

    _assert_field_map_conservative(field_map, source=source, source_file=source_file)
    return field_map


def write_aas_session_manager_no_mutation_adapter_field_map(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the deterministic no-mutation adapter field map."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    field_map = build_aas_session_manager_no_mutation_adapter_field_map(artifact_dir=base_dir)
    path = base_dir / AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME
    path.write_text(json.dumps(field_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_session_manager_no_mutation_adapter_field_map(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted no-mutation adapter field map."""

    base_dir = Path(artifact_dir) if artifact_dir else _default_proof_block_dir()
    path = base_dir / AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_FILENAME
    field_map = json.loads(path.read_text(encoding="utf-8"))
    source = load_aas_memory_acontext_readiness_carry_forward_card(artifact_dir=base_dir)
    source_file = base_dir / AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_FILENAME
    _assert_field_map_conservative(field_map, source=source, source_file=source_file)
    if field_map != build_aas_session_manager_no_mutation_adapter_field_map(
        artifact_dir=base_dir,
        carry_forward_card=source,
    ):
        raise CityOpsContractError("AAS session-manager no-mutation adapter field map fixture drift")
    return field_map


def _allowed_adapter_fields(source: dict[str, Any]) -> list[dict[str, Any]]:
    source_fields = {
        item["field"]: item
        for item in source.get("disabled_adapter_required_field_contract", [])
    }
    mappings = [
        ("proof_anchor_id", "proof_anchor_ref"),
        ("coordination_session_id_alias", "session_alias"),
        ("review_packet_id", "review_packet_ref"),
        ("compact_decision_id", "compact_decision_ref"),
        ("source_artifact_digests", "source_artifact_digests"),
        ("safe_to_claim", "safe_to_claim"),
        ("do_not_claim_yet", "do_not_claim_yet"),
        ("next_required_gate", "next_required_gate"),
        ("kill_switch_default", "kill_switch_default"),
    ]
    allowed: list[dict[str, Any]] = []
    for source_field, adapter_field in mappings:
        if source_field not in source_fields:
            raise CityOpsContractError(f"carry-forward source missing adapter field: {source_field}")
        allowed.append(
            {
                "adapter_field": adapter_field,
                "source_field": source_field,
                "required": True,
                "source_class_allowed": source_fields[source_field]["source_class_allowed"],
                "may_contain_private_context": False,
                "raw_identifier_allowed": False,
                "customer_or_worker_visible": False,
            }
        )
    return allowed


def _excluded_fields_forever() -> list[dict[str, Any]]:
    return [
        {
            "field_class": "raw_session_or_message_identifiers",
            "examples": ["raw_session_id", "raw_message_id", "chat_id", "message_id"],
            "reason": "future adapters may carry only sanitized aliases and reviewed artifact refs",
        },
        {
            "field_class": "raw_transcripts_or_unreviewed_memory",
            "examples": ["transcript", "raw_chat_log", "unreviewed_memory_blob"],
            "reason": "memory inputs must be reviewed summaries, never transcript replay",
        },
        {
            "field_class": "private_operator_context_or_secrets",
            "examples": ["bearer_token", "api_secret", "operator_private_note"],
            "reason": "adapter shape must be safe to inspect and commit without private context",
        },
        {
            "field_class": "exact_gps_or_raw_metadata",
            "examples": ["latitude", "longitude", "raw_exif", "device_metadata"],
            "reason": "location and raw metadata release require separate privacy authority",
        },
        {
            "field_class": "customer_public_worker_surfaces",
            "examples": ["customer_copy", "public_route", "worker_instruction"],
            "reason": "session-manager adapter shape is not a delivery/publication/worker-doctrine gate",
        },
        {
            "field_class": "launch_or_settlement_controls",
            "examples": ["price_quote", "queue_launch", "dispatch_instruction", "reputation_event", "payment_readiness_claim"],
            "reason": "pricing, dispatch, reputation, and payment require separate proof gates",
        },
        {
            "field_class": "stopped_project_inputs",
            "examples": ["autojob_history", "frontier_academy_content", "kk_v2_swarm_state", "karmacadabra_v2_context"],
            "reason": "DREAM-PRIORITIES.md explicitly stops these tracks for dream work",
        },
    ]


def _adapter_runtime_defaults() -> dict[str, bool | str]:
    return {
        "default_decision": "hold_no_runtime_mutation",
        "kill_switch_default": "disabled",
        "register_adapter": False,
        "enable_adapter": False,
        "write_session_manager_config": False,
        "mutate_session_manager_state": False,
        "write_live_acontext": False,
        "retrieve_live_acontext": False,
        "autoroute_cross_project": False,
        "emit_customer_copy": False,
        "emit_worker_instruction": False,
        "launch_queue_or_dispatch": False,
        "emit_reputation_or_worker_skill_dna": False,
    }


def _readiness_flags() -> dict[str, bool]:
    return {
        "session_manager_no_mutation_field_map_landed": True,
        "source_carry_forward_card_validated": True,
        "allowed_adapter_fields_named": True,
        "excluded_fields_named": True,
        "adapter_runtime_defaults_named": True,
        "operator_answer_absent": True,
        "operator_approval_record_absent": True,
        "default_hold_no_runtime_mutation_applied": True,
        "safe_for_internal_admin_adapter_shape_reference": True,
        "safe_for_operator_answer_recording": False,
        "safe_for_operator_approval_recording": False,
        "safe_for_design_only_wiring_selection": False,
        "safe_for_bounded_local_activation_test_selection": False,
        "safe_for_runtime_adapter_registration": False,
        "safe_for_runtime_adapter_enablement": False,
        "safe_for_runtime_session_manager_mutation": False,
        "safe_for_session_manager_config_write": False,
        "safe_for_live_acontext_write_or_retrieval": False,
        "safe_for_cross_project_autorouting": False,
        "safe_for_customer_or_public_delivery": False,
        "safe_for_worker_instruction_or_doctrine": False,
        "safe_for_queue_launch_or_dispatch": False,
        "safe_for_reputation_or_worker_skill_dna": False,
        "safe_for_payment_or_production_claim": False,
        "safe_for_gps_or_raw_metadata_release": False,
        "safe_for_private_context_release": False,
        "safe_for_domain_legal_emergency_repair_insurance_or_sla_authority": False,
        "safe_for_stopped_project_integration": False,
        "general_acontext_sink_ready": False,
        "runtime_parity_proven": False,
        "operator_activation_approved": False,
    }


def _assert_carry_forward_source_conservative(source: dict[str, Any]) -> None:
    if source.get("schema") != AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SCHEMA:
        raise CityOpsContractError("unexpected memory-to-Acontext carry-forward source schema")
    if AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SAFE_CLAIM not in source.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("memory-to-Acontext carry-forward source safe claim missing")

    carry = source.get("readiness_carry_forward", {})
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
            raise CityOpsContractError(f"source carry-forward promoted: {key}")
    if carry.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source carry-forward current decision promoted")
    if carry.get("effective_decision_after_card") != "hold_no_runtime_mutation":
        raise CityOpsContractError("source carry-forward effective decision promoted")

    readiness = source.get("readiness", {})
    for key in [
        "readiness_carry_forward_card_landed",
        "source_daytime_handoff_packet_validated",
        "disabled_adapter_field_contract_named",
        "field_survival_rules_named",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_internal_admin_field_contract_reference",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"source carry-forward readiness missing: {key}")
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
            raise CityOpsContractError(f"source carry-forward readiness promoted: {key}")
    for key, value in source.get("access_flags", {}).items():
        if value is not False:
            raise CityOpsContractError(f"source carry-forward access flag promoted: {key}")
    for key, value in source.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"source carry-forward stopped project firewall promoted: {key}")


def _assert_field_map_conservative(
    field_map: dict[str, Any], *, source: dict[str, Any], source_file: Path
) -> None:
    _assert_carry_forward_source_conservative(source)
    if field_map.get("schema") != AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SCHEMA:
        raise CityOpsContractError("unexpected session-manager field map schema")
    if field_map.get("field_map_id") != AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_ID:
        raise CityOpsContractError("session-manager field map id drift")
    if field_map.get("status_verdict") != AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_VERDICT:
        raise CityOpsContractError("session-manager field map verdict drift")

    source_ref = field_map.get("source_artifacts", {}).get(
        "memory_acontext_readiness_carry_forward_card", {}
    )
    if source_ref.get("canonical_digest_sha256") != _stable_digest(source):
        raise CityOpsContractError("session-manager field map source canonical digest drift")
    if source_ref.get("file_digest_sha256") != _file_digest(source_file):
        raise CityOpsContractError("session-manager field map source file digest drift")
    if source_ref.get("safe_claim") != AAS_MEMORY_ACONTEXT_READINESS_CARRY_FORWARD_CARD_SAFE_CLAIM:
        raise CityOpsContractError("session-manager field map source safe claim drift")

    mapped = field_map.get("no_mutation_adapter_field_map", {})
    if mapped.get("field_map_landed") is not True:
        raise CityOpsContractError("session-manager field map landed flag missing")
    for key in [
        "explicit_operator_answer_present",
        "operator_approval_record_present",
        "design_only_wiring_authorized_now",
        "bounded_activation_test_authorized_now",
        "adapter_registration_authorized_now",
        "adapter_enablement_authorized_now",
        "session_manager_mutation_authorized_now",
    ]:
        if mapped.get(key) is not False:
            raise CityOpsContractError(f"session-manager field map promoted: {key}")
    if mapped.get("current_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("session-manager field map current decision drift")
    if mapped.get("effective_decision_after_field_map") != "hold_no_runtime_mutation":
        raise CityOpsContractError("session-manager field map effective decision drift")

    allowed = field_map.get("allowed_adapter_fields", [])
    allowed_names = {item.get("adapter_field") for item in allowed if item.get("required") is True}
    for field in {
        "proof_anchor_ref",
        "session_alias",
        "review_packet_ref",
        "compact_decision_ref",
        "source_artifact_digests",
        "safe_to_claim",
        "do_not_claim_yet",
        "next_required_gate",
        "kill_switch_default",
    }:
        if field not in allowed_names:
            raise CityOpsContractError(f"session-manager field map missing allowed adapter field: {field}")
    if any(item.get("may_contain_private_context") is not False for item in allowed):
        raise CityOpsContractError("session-manager field map allows private context")
    if any(item.get("raw_identifier_allowed") is not False for item in allowed):
        raise CityOpsContractError("session-manager field map allows raw identifiers")
    if any(item.get("customer_or_worker_visible") is not False for item in allowed):
        raise CityOpsContractError("session-manager field map allows customer/worker visibility")

    excluded = field_map.get("excluded_fields_forever", [])
    excluded_classes = {item.get("field_class") for item in excluded}
    for required_class in {
        "raw_session_or_message_identifiers",
        "raw_transcripts_or_unreviewed_memory",
        "private_operator_context_or_secrets",
        "exact_gps_or_raw_metadata",
        "customer_public_worker_surfaces",
        "launch_or_settlement_controls",
        "stopped_project_inputs",
    }:
        if required_class not in excluded_classes:
            raise CityOpsContractError(f"session-manager field map missing excluded class: {required_class}")

    defaults = field_map.get("adapter_runtime_defaults", {})
    if defaults.get("default_decision") != "hold_no_runtime_mutation":
        raise CityOpsContractError("session-manager field map default decision drift")
    if defaults.get("kill_switch_default") != "disabled":
        raise CityOpsContractError("session-manager field map kill switch drift")
    for key, value in defaults.items():
        if key not in {"default_decision", "kill_switch_default"} and value is not False:
            raise CityOpsContractError(f"session-manager field map runtime default promoted: {key}")

    if any(gate.get("passed_now") is not False for gate in field_map.get("future_gate_order", [])):
        raise CityOpsContractError("session-manager field map future gate already passed")
    for key, value in field_map.get("stopped_project_firewall", {}).items():
        if key.endswith("_work_allowed") and value is not False:
            raise CityOpsContractError(f"session-manager field map stopped project firewall promoted: {key}")
    for key, expected in _FALSE_ACCESS_FLAGS.items():
        if field_map.get("access_flags", {}).get(key) is not expected:
            raise CityOpsContractError(f"session-manager field map access flag drift: {key}")

    readiness = field_map.get("readiness", {})
    for key in [
        "session_manager_no_mutation_field_map_landed",
        "source_carry_forward_card_validated",
        "allowed_adapter_fields_named",
        "excluded_fields_named",
        "adapter_runtime_defaults_named",
        "operator_answer_absent",
        "operator_approval_record_absent",
        "default_hold_no_runtime_mutation_applied",
        "safe_for_internal_admin_adapter_shape_reference",
    ]:
        if readiness.get(key) is not True:
            raise CityOpsContractError(f"session-manager field map readiness missing: {key}")
    for key, value in readiness.items():
        if key not in {
            "session_manager_no_mutation_field_map_landed",
            "source_carry_forward_card_validated",
            "allowed_adapter_fields_named",
            "excluded_fields_named",
            "adapter_runtime_defaults_named",
            "operator_answer_absent",
            "operator_approval_record_absent",
            "default_hold_no_runtime_mutation_applied",
            "safe_for_internal_admin_adapter_shape_reference",
        } and value is not False:
            raise CityOpsContractError(f"session-manager field map readiness promoted: {key}")

    _assert_claim_boundaries(
        field_map.get("claim_boundaries", {}).get("safe_to_claim", []),
        field_map.get("claim_boundaries", {}).get("do_not_claim_yet", []),
    )
    if AAS_SESSION_MANAGER_NO_MUTATION_ADAPTER_FIELD_MAP_SAFE_CLAIM not in field_map.get(
        "claim_boundaries", {}
    ).get("safe_to_claim", []):
        raise CityOpsContractError("session-manager field map missing safe claim")
    missing_blocked = set(SESSION_MANAGER_FIELD_MAP_BLOCKED_CLAIMS) - set(
        field_map.get("claim_boundaries", {}).get("do_not_claim_yet", [])
    )
    if missing_blocked:
        raise CityOpsContractError(
            f"session-manager field map missing blocked claims: {sorted(missing_blocked)}"
        )

    guidance = field_map.get("operator_guidance", {})
    if guidance.get("stop_line") != SESSION_MANAGER_FIELD_MAP_STOP_LINE:
        raise CityOpsContractError("session-manager field map stop line drift")
    if guidance.get("not_customer_copy") is not True or guidance.get("not_worker_instruction") is not True:
        raise CityOpsContractError("session-manager field map external guidance drift")

    serialized = json.dumps(field_map, sort_keys=True).lower()
    for pattern in _SECRET_OR_IDENTIFIER_PATTERNS:
        if pattern.search(serialized):
            raise CityOpsContractError("session-manager field map persisted secret, identifier, or PII pattern")


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
