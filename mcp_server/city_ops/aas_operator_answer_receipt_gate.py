"""Internal/admin AAS operator answer receipt gate.

This gate consumes the current read-only AAS operator cockpit and defines a
machine-checkable contract for a future explicit operator answer receipt. It
records no answer, approval, runtime change, product exposure, public/customer
surface, worker instruction, dispatch, reputation signal, payment claim, or
stopped-project integration.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .aas_operator_cockpit_read_surface import (
    AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME,
    AAS_OPERATOR_COCKPIT_READ_SURFACE_SAFE_CLAIM,
    AAS_OPERATOR_COCKPIT_READ_SURFACE_SCHEMA,
    AAS_OPERATOR_COCKPIT_READ_SURFACE_STATUS,
    COCKPIT_BLOCKED_CLAIMS,
    COCKPIT_FALSE_FLAGS,
    load_aas_operator_cockpit_read_surface,
)
from .aas_two_lane_operator_answer_schema import (
    ALLOWED_FUTURE_DECISIONS,
    DEFAULT_EFFECTIVE_DECISION,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_OPERATOR_ANSWER_RECEIPT_GATE_SCHEMA = (
    "city_ops.aas_operator_answer_receipt_gate.v1"
)
AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME = "aas_operator_answer_receipt_gate.json"
AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM = (
    "internal_admin_aas_operator_answer_receipt_gate_landed"
)
AAS_OPERATOR_ANSWER_RECEIPT_GATE_ID = (
    "execution_market.aas.operator_answer_receipt_gate.2026_06_05_0200"
)
AAS_OPERATOR_ANSWER_RECEIPT_GATE_STATUS = (
    "schema_gate_only_no_answer_no_approval_no_runtime_or_external_promotion"
)
FUTURE_RECEIPT_SCHEMA = "city_ops.aas_operator_answer_receipt.v1"
SOURCE_COCKPIT_REF = (
    f"mcp_server/city_ops/fixtures/aas_package_ladder/"
    f"{AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME}"
)

RECEIPT_REQUIRED_FIELDS = [
    "answer_receipt_id",
    "receipt_schema",
    "source_cockpit_ref",
    "source_cockpit_digest_sha256",
    "operator_answer_value",
    "operator_answer_recorded",
    "operator_approval_recorded",
    "explicit_operator_reference",
    "approval_evidence_ref",
    "approved_sections",
    "held_sections",
    "redactions_passed",
    "delivery_path_authorized",
    "runtime_path_authorized",
    "blocked_claims_preserved",
    "next_required_gate",
]

NO_MOVEMENT_VALUES = ["keep_both_lanes_held", "pause_aas_proof_layering"]
NEXT_REQUIRED_GATE_BY_VALUE = {
    "keep_both_lanes_held": "stop_no_movement_keep_both_lanes_held",
    "pause_aas_proof_layering": "stop_no_movement_pause_proof_layering",
    "create_retail_reality_answer_or_hold_record": (
        "create_retail_reality_answer_or_hold_record_before_any_public_or_dispatch_step"
    ),
    "create_runtime_memory_operator_answer_record": (
        "create_runtime_memory_operator_answer_record_then_restore_docker_and_rerun_read_only_inventory"
    ),
}

OPERATOR_REFERENCE_MAX_LENGTH = 240
ANSWER_RECEIPT_ID_MAX_LENGTH = 160
ANSWER_RECEIPT_ID_PATTERN = re.compile(
    r"^execution_market\.aas\.operator_answer\.\d{4}_\d{2}_\d{2}\.[a-z0-9][a-z0-9_-]{2,80}$"
)
DISALLOWED_OPERATOR_REFERENCE_PATTERNS = {
    "email_address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "decimal_coordinate_pair": re.compile(
        r"(?<!\d)-?\d{1,2}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}(?!\d)"
    ),
    "gps_coordinate_label": re.compile(
        r"\b(?:gps|lat(?:itude)?|lng|lon(?:gitude)?)\s*[:=]", re.I
    ),
    "phone_number": re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)"),
    "ethereum_private_key": re.compile(r"\b0x[a-fA-F0-9]{64}\b"),
    "openai_or_similar_api_key": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "github_token": re.compile(r"\bgh[opsu]_[A-Za-z0-9_]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
}

RECEIPT_GATE_FALSE_FLAGS = {
    "operator_answer_recorded": False,
    "operator_approval_recorded": False,
    "future_answer_receipt_created": False,
    "retail_reality_answer_or_hold_record_created": False,
    "runtime_memory_operator_answer_record_created": False,
    "product_exposure_approved": False,
    "runtime_memory_wiring_approved": False,
    "delivery_path_authorized": False,
    "runtime_path_authorized": False,
    "runtime_adapter_registered": False,
    "runtime_adapter_enabled": False,
    "irc_session_manager_mutated": False,
    "live_acontext_write_or_retrieval_enabled": False,
    "customer_visible": False,
    "public_visible": False,
    "worker_visible": False,
    "catalog_visible": False,
    "pricing_enabled": False,
    "queue_launch_ready": False,
    "dispatch_enabled": False,
    "erc8004_reputation_ready": False,
    "worker_skill_dna_ready": False,
    "payment_or_production_reverified": False,
    "exact_gps_or_raw_metadata_release_allowed": False,
    "private_context_release_allowed": False,
    "domain_authority_claims_allowed": False,
    "worker_copyable_doctrine_ready": False,
    "stopped_project_integration_ready": False,
}

RECEIPT_GATE_BLOCKED_CLAIMS = [
    *COCKPIT_BLOCKED_CLAIMS,
    "answer_receipt_gate_records_operator_answer",
    "answer_receipt_gate_records_operator_approval",
    "answer_receipt_gate_creates_future_answer_receipt",
    "answer_receipt_gate_treats_cockpit_display_as_answer",
    "answer_receipt_gate_accepts_missing_explicit_operator_reference",
    "answer_receipt_gate_accepts_unapproved_public_delivery",
    "answer_receipt_gate_accepts_unverified_runtime_path",
    "answer_receipt_gate_creates_retail_reality_answer_or_hold_record",
    "answer_receipt_gate_creates_runtime_memory_operator_answer_record",
    "answer_receipt_gate_approves_product_exposure",
    "answer_receipt_gate_approves_runtime_memory_wiring",
    "answer_receipt_gate_registers_or_enables_runtime_adapter",
    "answer_receipt_gate_mutates_irc_session_manager",
    "answer_receipt_gate_writes_or_retrieves_live_acontext",
    "answer_receipt_gate_creates_customer_public_worker_surface",
    "answer_receipt_gate_authorizes_catalog_pricing_queue_or_dispatch",
    "answer_receipt_gate_emits_erc8004_reputation_or_worker_skill_dna",
    "answer_receipt_gate_reverifies_payment_or_production",
    "answer_receipt_gate_releases_exact_gps_or_raw_metadata",
    "answer_receipt_gate_releases_private_context",
    "answer_receipt_gate_grants_domain_authority_claims",
    "answer_receipt_gate_publishes_worker_copyable_doctrine",
    "answer_receipt_gate_integrates_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(RECEIPT_GATE_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "future_answer_receipt_created",
    "answer_record_created",
    "product_exposure_approved",
    "runtime_memory_wiring_approved",
    "delivery_path_authorized",
    "runtime_path_authorized",
    "runtime_adapter_registered",
    "runtime_adapter_enabled",
    "irc_session_manager_mutated",
    "live_acontext_ready",
    "runtime_parity_proven",
    "cross_project_autorouting_ready",
    "customer_copy_ready",
    "public_dashboard_ready",
    "catalog_ready",
    "pricing_ready",
    "dispatch_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "private_context_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
    "autojob_integration_ready",
    "frontier_academy_expansion_ready",
    "kk_v2_swarm_ready",
    "karmacadabra_v2_ready",
}


def _stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _assert_source_cockpit(cockpit: dict[str, Any]) -> None:
    if cockpit.get("schema") != AAS_OPERATOR_COCKPIT_READ_SURFACE_SCHEMA:
        raise CityOpsContractError("AAS answer receipt gate source cockpit schema drift")
    if cockpit.get("cockpit_status") != AAS_OPERATOR_COCKPIT_READ_SURFACE_STATUS:
        raise CityOpsContractError("AAS answer receipt gate source cockpit status drift")
    safe = set(cockpit.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_OPERATOR_COCKPIT_READ_SURFACE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS answer receipt gate source safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS answer receipt gate source forbidden safe claims: {sorted(forbidden_safe)}"
        )
    blocked = set(cockpit.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing_blocked = set(COCKPIT_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS answer receipt gate source missing blocked claims: {sorted(missing_blocked)}"
        )

    answer_panel = cockpit.get("answer_panel", {})
    decisions = answer_panel.get("allowed_future_decisions", [])
    if [item.get("decision") for item in decisions] != ALLOWED_FUTURE_DECISIONS:
        raise CityOpsContractError("AAS answer receipt gate source allowed decisions drift")
    if answer_panel.get("display_text_is_not_answer") is not True:
        raise CityOpsContractError("AAS answer receipt gate source display became answer")
    for item in decisions:
        if item.get("selected_by_this_cockpit") is not False:
            raise CityOpsContractError("AAS answer receipt gate source selected decision")
        if item.get("approval_granted_by_this_cockpit") is not False:
            raise CityOpsContractError("AAS answer receipt gate source granted approval")

    current = cockpit.get("current_no_answer_decision", {})
    if current.get("operator_answer_recorded") is not False:
        raise CityOpsContractError("AAS answer receipt gate source recorded answer")
    if current.get("operator_approval_recorded") is not False:
        raise CityOpsContractError("AAS answer receipt gate source recorded approval")
    if current.get("selected_future_answer") is not None:
        raise CityOpsContractError("AAS answer receipt gate source selected future answer")
    if current.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS answer receipt gate source effective decision drift")

    readiness = cockpit.get("readiness", {})
    for key, expected in COCKPIT_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS answer receipt gate source promoted {key}")
    firewall = cockpit.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS answer receipt gate source allowed {key}")


def _future_receipt_field_contracts(cockpit: dict[str, Any]) -> list[dict[str, Any]]:
    source_digest = _stable_digest(cockpit)
    expected_values: dict[str, Any] = {
        "answer_receipt_id": "execution_market.aas.operator_answer.<date>.<short_label>",
        "receipt_schema": FUTURE_RECEIPT_SCHEMA,
        "source_cockpit_ref": SOURCE_COCKPIT_REF,
        "source_cockpit_digest_sha256": source_digest,
        "operator_answer_value": ALLOWED_FUTURE_DECISIONS,
        "operator_answer_recorded": True,
        "operator_approval_recorded": "boolean; true only with explicit approval evidence",
        "explicit_operator_reference": (
            "opaque_non_secret_non_doxxing_reference_to_human_or_operator_answer; "
            "no raw emails phones exact coordinates gps labels private keys api tokens or secrets"
        ),
        "approval_evidence_ref": "required_non_empty_when_operator_approval_recorded_true",
        "approved_sections": "list; must be empty unless separately approved",
        "held_sections": "list; preserve held claims and blocked surfaces",
        "redactions_passed": "boolean; true only after separate redaction proof",
        "delivery_path_authorized": False,
        "runtime_path_authorized": False,
        "blocked_claims_preserved": True,
        "next_required_gate": NEXT_REQUIRED_GATE_BY_VALUE,
    }
    return [
        {
            "field": field,
            "required_in_future_receipt": True,
            "satisfied_by_this_gate": False,
            "expected_value_or_constraint": expected_values[field],
        }
        for field in RECEIPT_REQUIRED_FIELDS
    ]


def build_aas_operator_answer_receipt_gate(
    *,
    artifact_dir: str | Path | None = None,
    source_cockpit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a schema gate for future explicit AAS operator answer receipts."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    cockpit = source_cockpit or load_aas_operator_cockpit_read_surface(
        artifact_dir=source_dir
    )
    _assert_source_cockpit(cockpit)

    safe_to_claim = _dedupe(
        [
            *cockpit["claim_boundaries"]["safe_to_claim"],
            AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *cockpit["claim_boundaries"]["do_not_claim_yet"],
            *RECEIPT_GATE_BLOCKED_CLAIMS,
        ]
    )

    gate = {
        "schema": AAS_OPERATOR_ANSWER_RECEIPT_GATE_SCHEMA,
        "gate_id": AAS_OPERATOR_ANSWER_RECEIPT_GATE_ID,
        "scope": "internal_admin_schema_gate_for_future_explicit_aas_operator_answer_receipt",
        "gate_status": AAS_OPERATOR_ANSWER_RECEIPT_GATE_STATUS,
        "future_receipt_schema": FUTURE_RECEIPT_SCHEMA,
        "source_cockpit": {
            "file": AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME,
            "ref": SOURCE_COCKPIT_REF,
            "schema": cockpit["schema"],
            "cockpit_id": cockpit["cockpit_id"],
            "safe_claim": AAS_OPERATOR_COCKPIT_READ_SURFACE_SAFE_CLAIM,
            "digest_sha256": _stable_digest(cockpit),
            "default_if_no_human_answer": DEFAULT_EFFECTIVE_DECISION,
        },
        "allowed_operator_answer_values": [
            {
                "value": value,
                "accepted_by_future_receipt": True,
                "selected_by_this_gate": False,
                "approval_granted_by_this_gate": False,
                "delivery_path_authorized_by_this_gate": False,
                "runtime_path_authorized_by_this_gate": False,
                "next_required_gate_if_explicitly_chosen": NEXT_REQUIRED_GATE_BY_VALUE[value],
            }
            for value in ALLOWED_FUTURE_DECISIONS
        ],
        "future_receipt_required_fields": _future_receipt_field_contracts(cockpit),
        "current_values": {
            "operator_answer_recorded": False,
            "operator_approval_recorded": False,
            "selected_operator_answer_value": None,
            "future_answer_receipt_created": False,
            "effective_decision": DEFAULT_EFFECTIVE_DECISION,
            "cockpit_display_is_answer": False,
            "gate_is_answer_receipt": False,
        },
        "receipt_validation_policy": {
            "requires_explicit_operator_reference": True,
            "rejects_private_or_secret_operator_reference": True,
            "requires_source_cockpit_digest_match": True,
            "allows_cockpit_display_as_answer": False,
            "allows_public_delivery_authorization": False,
            "allows_runtime_path_authorization": False,
            "requires_blocked_claims_preserved": True,
            "approval_true_requires_approval_evidence_ref": True,
            "requires_safe_answer_receipt_id": True,
            "answer_receipt_id_format": (
                "execution_market.aas.operator_answer.YYYY_MM_DD.<opaque_short_label>"
            ),
            "answer_receipt_id_max_length": ANSWER_RECEIPT_ID_MAX_LENGTH,
            "approved_sections_require_approval_and_redaction": True,
            "held_sections_must_be_non_empty": True,
            "no_movement_values": NO_MOVEMENT_VALUES,
            "product_value_next_gate": NEXT_REQUIRED_GATE_BY_VALUE[
                "create_retail_reality_answer_or_hold_record"
            ],
            "runtime_value_next_gate": NEXT_REQUIRED_GATE_BY_VALUE[
                "create_runtime_memory_operator_answer_record"
            ],
            "explicit_operator_reference_max_length": OPERATOR_REFERENCE_MAX_LENGTH,
            "disallowed_operator_reference_material": sorted(
                DISALLOWED_OPERATOR_REFERENCE_PATTERNS.keys()
            ),
        },
        "readiness": {
            "internal_admin_answer_receipt_gate_landed": True,
            "source_cockpit_verified": True,
            "future_receipt_shape_constrained": True,
            "default_off_non_authorizing": True,
            **RECEIPT_GATE_FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "still_blocked_claims": do_not_claim_yet,
        "stopped_project_firewall": {
            "autojob_work_allowed": False,
            "frontier_academy_work_allowed": False,
            "kk_v2_work_allowed": False,
            "karmacadabra_v2_work_allowed": False,
            "source": "DREAM-PRIORITIES.md explicit stop list",
        },
        "operator_guidance": {
            "first_read": "DREAM-PRIORITIES.md",
            "use_this_gate_for": "validate_a_future_explicit_answer_receipt_before_any_movement",
            "do_not_fill_receipt_from_this_gate": True,
            "do_not_treat_cockpit_display_as_answer": True,
            "if_no_real_answer": "stop_at_pause_aas_proof_layering_or_keep_both_lanes_held",
            "not_public_dashboard": True,
            "not_customer_copy": True,
            "not_worker_instruction": True,
            "not_runtime_adapter": True,
        },
        "gate_verdict": (
            "answer_receipt_gate_landed_schema_only_no_answer_no_approval_no_runtime_"
            "product_delivery_reputation_payment_dispatch_public_surface_or_stopped_project_promotion"
        ),
    }
    _assert_aas_operator_answer_receipt_gate(gate, source_cockpit=cockpit)
    return gate


def _assert_aas_operator_answer_receipt_gate(
    gate: dict[str, Any], *, source_cockpit: dict[str, Any]
) -> None:
    _assert_source_cockpit(source_cockpit)
    if gate.get("schema") != AAS_OPERATOR_ANSWER_RECEIPT_GATE_SCHEMA:
        raise CityOpsContractError("AAS answer receipt gate schema drift")
    if gate.get("gate_id") != AAS_OPERATOR_ANSWER_RECEIPT_GATE_ID:
        raise CityOpsContractError("AAS answer receipt gate id drift")
    if gate.get("gate_status") != AAS_OPERATOR_ANSWER_RECEIPT_GATE_STATUS:
        raise CityOpsContractError("AAS answer receipt gate status drift")
    if gate.get("future_receipt_schema") != FUTURE_RECEIPT_SCHEMA:
        raise CityOpsContractError("AAS answer receipt future schema drift")

    source = gate.get("source_cockpit", {})
    if source.get("file") != AAS_OPERATOR_COCKPIT_READ_SURFACE_FILENAME:
        raise CityOpsContractError("AAS answer receipt gate source file drift")
    if source.get("digest_sha256") != _stable_digest(source_cockpit):
        raise CityOpsContractError("AAS answer receipt gate source digest drift")
    if source.get("default_if_no_human_answer") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS answer receipt gate default decision drift")

    values = gate.get("allowed_operator_answer_values", [])
    if [item.get("value") for item in values] != ALLOWED_FUTURE_DECISIONS:
        raise CityOpsContractError("AAS answer receipt gate allowed values drift")
    for item in values:
        for key in [
            "selected_by_this_gate",
            "approval_granted_by_this_gate",
            "delivery_path_authorized_by_this_gate",
            "runtime_path_authorized_by_this_gate",
        ]:
            if item.get(key) is not False:
                raise CityOpsContractError(f"AAS answer receipt gate promoted {key}")
        if item.get("next_required_gate_if_explicitly_chosen") != NEXT_REQUIRED_GATE_BY_VALUE[
            item["value"]
        ]:
            raise CityOpsContractError("AAS answer receipt gate next gate drift")

    fields = gate.get("future_receipt_required_fields", [])
    if [item.get("field") for item in fields] != RECEIPT_REQUIRED_FIELDS:
        raise CityOpsContractError("AAS answer receipt gate required fields drift")
    for item in fields:
        if item.get("required_in_future_receipt") is not True:
            raise CityOpsContractError("AAS answer receipt gate field not required")
        if item.get("satisfied_by_this_gate") is not False:
            raise CityOpsContractError("AAS answer receipt gate satisfied a future field")

    current = gate.get("current_values", {})
    for key in [
        "operator_answer_recorded",
        "operator_approval_recorded",
        "future_answer_receipt_created",
        "cockpit_display_is_answer",
        "gate_is_answer_receipt",
    ]:
        if current.get(key) is not False:
            raise CityOpsContractError(f"AAS answer receipt gate promoted {key}")
    if current.get("selected_operator_answer_value") is not None:
        raise CityOpsContractError("AAS answer receipt gate selected value")
    if current.get("effective_decision") != DEFAULT_EFFECTIVE_DECISION:
        raise CityOpsContractError("AAS answer receipt gate effective decision drift")

    policy = gate.get("receipt_validation_policy", {})
    for key in [
        "requires_explicit_operator_reference",
        "rejects_private_or_secret_operator_reference",
        "requires_source_cockpit_digest_match",
        "requires_blocked_claims_preserved",
        "approval_true_requires_approval_evidence_ref",
        "requires_safe_answer_receipt_id",
        "approved_sections_require_approval_and_redaction",
        "held_sections_must_be_non_empty",
    ]:
        if policy.get(key) is not True:
            raise CityOpsContractError(f"AAS answer receipt gate disabled policy {key}")
    for key in [
        "allows_cockpit_display_as_answer",
        "allows_public_delivery_authorization",
        "allows_runtime_path_authorization",
    ]:
        if policy.get(key) is not False:
            raise CityOpsContractError(f"AAS answer receipt gate allowed policy {key}")

    readiness = gate.get("readiness", {})
    for key, expected in RECEIPT_GATE_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"AAS answer receipt gate promoted readiness {key}")

    safe = set(gate.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(gate.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS answer receipt gate safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS answer receipt gate forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(RECEIPT_GATE_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS answer receipt gate missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(f"AAS answer receipt gate claim overlap: {sorted(overlap)}")
    if gate.get("still_blocked_claims") != gate.get("claim_boundaries", {}).get(
        "do_not_claim_yet"
    ):
        raise CityOpsContractError("AAS answer receipt gate blocked claims drift")

    firewall = gate.get("stopped_project_firewall", {})
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"AAS answer receipt gate allowed {key}")


def validate_aas_operator_answer_receipt(
    receipt: dict[str, Any],
    *,
    artifact_dir: str | Path | None = None,
    gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a future explicit operator answer receipt against this gate.

    The validator accepts only receipt objects that already contain explicit
    operator-answer evidence. It does not create, select, approve, publish,
    dispatch, mutate runtime, emit reputation, or promote stopped projects.
    """

    source_gate = gate or build_aas_operator_answer_receipt_gate(artifact_dir=artifact_dir)
    missing = [field for field in RECEIPT_REQUIRED_FIELDS if field not in receipt]
    if missing:
        raise CityOpsContractError(
            f"AAS operator answer receipt missing required fields: {missing}"
        )
    if receipt.get("receipt_schema") != FUTURE_RECEIPT_SCHEMA:
        raise CityOpsContractError("AAS operator answer receipt schema drift")
    _assert_answer_receipt_id_is_safe(receipt.get("answer_receipt_id"))
    if receipt.get("source_cockpit_ref") != SOURCE_COCKPIT_REF:
        raise CityOpsContractError("AAS operator answer receipt source ref drift")
    if receipt.get("source_cockpit_digest_sha256") != source_gate["source_cockpit"][
        "digest_sha256"
    ]:
        raise CityOpsContractError("AAS operator answer receipt source digest drift")

    value = receipt.get("operator_answer_value")
    if value not in ALLOWED_FUTURE_DECISIONS:
        raise CityOpsContractError("AAS operator answer receipt invalid answer value")
    if receipt.get("operator_answer_recorded") is not True:
        raise CityOpsContractError("AAS operator answer receipt lacks explicit answer record")
    _assert_explicit_operator_reference_is_safe(receipt.get("explicit_operator_reference"))
    if not isinstance(receipt.get("operator_approval_recorded"), bool):
        raise CityOpsContractError("AAS operator answer receipt approval flag is not boolean")
    if receipt["operator_approval_recorded"] is True and not str(
        receipt.get("approval_evidence_ref", "")
    ).strip():
        raise CityOpsContractError("AAS operator answer receipt lacks approval evidence")

    for list_field in ["approved_sections", "held_sections"]:
        if not isinstance(receipt.get(list_field), list):
            raise CityOpsContractError(
                f"AAS operator answer receipt {list_field} must be a list"
            )
        if not all(isinstance(item, str) and item.strip() for item in receipt[list_field]):
            raise CityOpsContractError(
                f"AAS operator answer receipt {list_field} must contain only non-empty strings"
            )
    if receipt.get("approved_sections") and (
        receipt["operator_approval_recorded"] is not True
        or receipt.get("redactions_passed") is not True
    ):
        raise CityOpsContractError(
            "AAS operator answer receipt approved sections require approval and redaction proof"
        )
    if not receipt.get("held_sections"):
        raise CityOpsContractError(
            "AAS operator answer receipt held sections must preserve at least one hold"
        )
    if receipt.get("blocked_claims_preserved") is not True:
        raise CityOpsContractError("AAS operator answer receipt did not preserve blocked claims")
    for bool_field in [
        "redactions_passed",
        "delivery_path_authorized",
        "runtime_path_authorized",
    ]:
        if not isinstance(receipt.get(bool_field), bool):
            raise CityOpsContractError(
                f"AAS operator answer receipt {bool_field} must be boolean"
            )
    if receipt.get("delivery_path_authorized") is not False:
        raise CityOpsContractError("AAS operator answer receipt authorized delivery too early")
    if receipt.get("runtime_path_authorized") is not False:
        raise CityOpsContractError("AAS operator answer receipt authorized runtime too early")
    if receipt.get("next_required_gate") != NEXT_REQUIRED_GATE_BY_VALUE[value]:
        raise CityOpsContractError("AAS operator answer receipt next gate mismatch")

    return {
        "receipt_valid": True,
        "accepted_operator_answer_value": value,
        "next_required_gate": NEXT_REQUIRED_GATE_BY_VALUE[value],
        "delivery_path_authorized": False,
        "runtime_path_authorized": False,
        "blocked_claims_preserved": True,
    }


def _assert_answer_receipt_id_is_safe(answer_receipt_id: Any) -> None:
    if not isinstance(answer_receipt_id, str) or not answer_receipt_id.strip():
        raise CityOpsContractError("AAS operator answer receipt lacks receipt id")
    normalized = answer_receipt_id.strip()
    if len(normalized) > ANSWER_RECEIPT_ID_MAX_LENGTH:
        raise CityOpsContractError("AAS operator answer receipt id too long")
    if not ANSWER_RECEIPT_ID_PATTERN.fullmatch(normalized):
        raise CityOpsContractError("AAS operator answer receipt id format drift")
    for label, pattern in DISALLOWED_OPERATOR_REFERENCE_PATTERNS.items():
        if pattern.search(normalized):
            raise CityOpsContractError(
                "AAS operator answer receipt id includes disallowed private data: "
                f"{label}"
            )


def _assert_explicit_operator_reference_is_safe(reference: Any) -> None:
    if not isinstance(reference, str) or not reference.strip():
        raise CityOpsContractError("AAS operator answer receipt lacks explicit reference")
    normalized = reference.strip()
    if len(normalized) > OPERATOR_REFERENCE_MAX_LENGTH:
        raise CityOpsContractError("AAS operator answer receipt explicit reference too long")
    for label, pattern in DISALLOWED_OPERATOR_REFERENCE_PATTERNS.items():
        if pattern.search(normalized):
            raise CityOpsContractError(
                "AAS operator answer receipt explicit reference includes disallowed "
                f"private data: {label}"
            )


def write_aas_operator_answer_receipt_gate(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    gate = build_aas_operator_answer_receipt_gate(artifact_dir=target_dir)
    target_path = target_dir / AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME
    target_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target_path


def load_aas_operator_answer_receipt_gate(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME
    gate = json.loads(path.read_text(encoding="utf-8"))
    cockpit = load_aas_operator_cockpit_read_surface(artifact_dir=source_dir)
    _assert_aas_operator_answer_receipt_gate(gate, source_cockpit=cockpit)
    return gate
