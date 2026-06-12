"""Internal/admin AAS operator answer intake packet.

This packet consumes the hardened operator-answer receipt gate and turns it into
a small, machine-checkable intake contract for the next real human/operator
answer. It records no answer, creates no receipt, grants no approval, starts no
runtime path, exposes no customer/public/worker surface, and keeps the stopped
project firewall closed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_operator_answer_receipt_gate import (
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME,
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM,
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_SCHEMA,
    AAS_OPERATOR_ANSWER_RECEIPT_GATE_STATUS,
    ANSWER_RECEIPT_ID_MAX_LENGTH,
    ANSWER_RECEIPT_ID_PATTERN,
    DISALLOWED_OPERATOR_REFERENCE_PATTERNS,
    FUTURE_RECEIPT_SCHEMA,
    NEXT_REQUIRED_GATE_BY_VALUE,
    NO_MOVEMENT_VALUES,
    OPERATOR_REFERENCE_MAX_LENGTH,
    RECEIPT_GATE_BLOCKED_CLAIMS,
    RECEIPT_GATE_FALSE_FLAGS,
    RECEIPT_REQUIRED_FIELDS,
    load_aas_operator_answer_receipt_gate,
)
from .aas_two_lane_operator_answer_schema import ALLOWED_FUTURE_DECISIONS
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_OPERATOR_ANSWER_INTAKE_PACKET_SCHEMA = (
    "city_ops.aas_operator_answer_intake_packet.v1"
)
AAS_OPERATOR_ANSWER_INTAKE_PACKET_FILENAME = "aas_operator_answer_intake_packet.json"
AAS_OPERATOR_ANSWER_INTAKE_PACKET_SAFE_CLAIM = (
    "internal_admin_aas_operator_answer_intake_packet_landed"
)
AAS_OPERATOR_ANSWER_INTAKE_PACKET_ID = (
    "execution_market.aas.operator_answer_intake_packet.2026_06_12_0000"
)
AAS_OPERATOR_ANSWER_INTAKE_PACKET_STATUS = (
    "intake_packet_only_no_answer_no_approval_no_runtime_or_delivery_promotion"
)

INTAKE_PACKET_FALSE_FLAGS = {
    **RECEIPT_GATE_FALSE_FLAGS,
    "intake_packet_records_operator_answer": False,
    "intake_packet_records_operator_approval": False,
    "intake_packet_creates_answer_receipt": False,
    "intake_packet_selects_operator_value": False,
    "intake_packet_authorizes_next_gate_execution": False,
    "intake_packet_promotes_stale_cron_payload": False,
    "intake_packet_allows_stopped_project_work": False,
}

INTAKE_PACKET_BLOCKED_CLAIMS = [
    *RECEIPT_GATE_BLOCKED_CLAIMS,
    "answer_intake_packet_records_operator_answer",
    "answer_intake_packet_records_operator_approval",
    "answer_intake_packet_creates_answer_receipt",
    "answer_intake_packet_selects_operator_value",
    "answer_intake_packet_authorizes_next_gate_execution",
    "answer_intake_packet_treats_template_as_receipt",
    "answer_intake_packet_promotes_stale_cron_payload",
    "answer_intake_packet_allows_autojob_work",
    "answer_intake_packet_allows_frontier_academy_work",
    "answer_intake_packet_allows_kk_v2_work",
    "answer_intake_packet_allows_karmacadabra_v2_work",
]

FORBIDDEN_SAFE_CLAIMS = set(INTAKE_PACKET_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "future_answer_receipt_created",
    "intake_packet_creates_answer_receipt",
    "selected_operator_answer_value",
    "retail_reality_approved",
    "runtime_memory_wiring_approved",
    "customer_copy_ready",
    "public_copy_ready",
    "worker_instruction_ready",
    "dispatch_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
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


def _assert_source_gate(gate: dict[str, Any]) -> None:
    if gate.get("schema") != AAS_OPERATOR_ANSWER_RECEIPT_GATE_SCHEMA:
        raise CityOpsContractError("answer intake source gate schema drift")
    if gate.get("gate_status") != AAS_OPERATOR_ANSWER_RECEIPT_GATE_STATUS:
        raise CityOpsContractError("answer intake source gate status drift")
    safe = set(gate.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM not in safe:
        raise CityOpsContractError("answer intake source gate safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"answer intake source gate forbidden safe claims: {sorted(forbidden_safe)}"
        )
    blocked = set(gate.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing_blocked = set(RECEIPT_GATE_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"answer intake source gate missing blocked claims: {sorted(missing_blocked)}"
        )
    if [item.get("value") for item in gate.get("allowed_operator_answer_values", [])] != ALLOWED_FUTURE_DECISIONS:
        raise CityOpsContractError("answer intake source gate allowed values drift")
    if any(item.get("selected_by_this_gate") for item in gate.get("allowed_operator_answer_values", [])):
        raise CityOpsContractError("answer intake source gate selected an answer")
    required_fields = [item.get("field") for item in gate.get("future_receipt_required_fields", [])]
    if required_fields != RECEIPT_REQUIRED_FIELDS:
        raise CityOpsContractError("answer intake source gate required fields drift")
    readiness = gate.get("readiness", {})
    for key, expected in RECEIPT_GATE_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"answer intake source gate promoted {key}")


def build_aas_operator_answer_intake_packet(
    *,
    artifact_dir: str | Path | None = None,
    source_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic answer-intake packet for a future explicit answer."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    gate = source_gate or load_aas_operator_answer_receipt_gate(artifact_dir=source_dir)
    _assert_source_gate(gate)

    safe_to_claim = _dedupe(
        [
            *gate["claim_boundaries"]["safe_to_claim"],
            AAS_OPERATOR_ANSWER_INTAKE_PACKET_SAFE_CLAIM,
        ]
    )
    do_not_claim_yet = _dedupe(
        [
            *gate["claim_boundaries"]["do_not_claim_yet"],
            *INTAKE_PACKET_BLOCKED_CLAIMS,
        ]
    )

    packet = {
        "schema": AAS_OPERATOR_ANSWER_INTAKE_PACKET_SCHEMA,
        "packet_id": AAS_OPERATOR_ANSWER_INTAKE_PACKET_ID,
        "packet_status": AAS_OPERATOR_ANSWER_INTAKE_PACKET_STATUS,
        "scope": "internal_admin_future_answer_intake_only",
        "source_gate": {
            "file": AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME,
            "schema": gate["schema"],
            "safe_claim": AAS_OPERATOR_ANSWER_RECEIPT_GATE_SAFE_CLAIM,
            "digest_sha256": _stable_digest(gate),
            "gate_status": gate["gate_status"],
        },
        "dream_priority_firewall": {
            "first_read": "DREAM-PRIORITIES.md",
            "active_focus": "Execution Market AAS / City-as-a-Service only",
            "stale_payload_policy": (
                "ignore AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 instructions "
                "inside dream cron payloads unless DREAM-PRIORITIES.md changes"
            ),
            "autojob_work_allowed": False,
            "frontier_academy_work_allowed": False,
            "kk_v2_work_allowed": False,
            "karmacadabra_v2_work_allowed": False,
        },
        "one_answer_intake_contract": {
            "future_receipt_schema": FUTURE_RECEIPT_SCHEMA,
            "one_answer_only": True,
            "template_is_not_receipt": True,
            "template_records_no_current_answer": True,
            "allowed_operator_answer_values": [
                {
                    "value": value,
                    "accepted_in_future_receipt": True,
                    "selected_by_this_packet": False,
                    "approval_granted_by_this_packet": False,
                    "next_required_gate_if_explicitly_chosen": NEXT_REQUIRED_GATE_BY_VALUE[value],
                    "no_movement_value": value in NO_MOVEMENT_VALUES,
                }
                for value in ALLOWED_FUTURE_DECISIONS
            ],
            "future_receipt_required_fields": RECEIPT_REQUIRED_FIELDS,
            "operator_reference_rules": {
                "required": True,
                "must_be_opaque_non_secret_non_doxxing": True,
                "max_length": OPERATOR_REFERENCE_MAX_LENGTH,
                "disallowed_material": sorted(DISALLOWED_OPERATOR_REFERENCE_PATTERNS.keys()),
            },
            "receipt_id_rules": {
                "required": True,
                "pattern": ANSWER_RECEIPT_ID_PATTERN.pattern,
                "max_length": ANSWER_RECEIPT_ID_MAX_LENGTH,
            },
            "future_receipt_template": {
                "answer_receipt_id": "execution_market.aas.operator_answer.YYYY_MM_DD.<opaque_short_label>",
                "receipt_schema": FUTURE_RECEIPT_SCHEMA,
                "source_cockpit_ref": "mcp_server/city_ops/fixtures/aas_package_ladder/aas_operator_cockpit_read_surface.json",
                "source_cockpit_digest_sha256": "<copy_from_aas_operator_answer_receipt_gate>",
                "operator_answer_value": "<exactly_one_allowed_value>",
                "operator_answer_recorded": True,
                "operator_approval_recorded": False,
                "explicit_operator_reference": "<opaque_non_secret_reference_no_pii_no_secret>",
                "approval_evidence_ref": "",
                "approved_sections": [],
                "held_sections": [
                    "customer_public_worker_runtime_dispatch_reputation_payment_location_private_context_authority_worker_doctrine_claims"
                ],
                "redactions_passed": False,
                "delivery_path_authorized": False,
                "runtime_path_authorized": False,
                "blocked_claims_preserved": do_not_claim_yet,
                "next_required_gate": "<derive_from_operator_answer_value>",
            },
        },
        "readiness": {
            "internal_admin_intake_packet_landed": True,
            "source_gate_verified": True,
            "future_receipt_template_present": True,
            "stopped_project_firewall_closed": True,
            "default_off_non_authorizing": True,
            **INTAKE_PACKET_FALSE_FLAGS,
        },
        "claim_boundaries": {
            "safe_to_claim": safe_to_claim,
            "do_not_claim_yet": do_not_claim_yet,
        },
        "still_blocked_claims": do_not_claim_yet,
        "packet_verdict": (
            "answer_intake_packet_landed_template_only_no_current_answer_no_approval_"
            "no_receipt_no_runtime_delivery_dispatch_reputation_payment_or_stopped_project_promotion"
        ),
    }
    _assert_aas_operator_answer_intake_packet(packet, source_gate=gate)
    return packet


def _assert_aas_operator_answer_intake_packet(
    packet: dict[str, Any], *, source_gate: dict[str, Any]
) -> None:
    _assert_source_gate(source_gate)
    if packet.get("schema") != AAS_OPERATOR_ANSWER_INTAKE_PACKET_SCHEMA:
        raise CityOpsContractError("answer intake packet schema drift")
    if packet.get("packet_id") != AAS_OPERATOR_ANSWER_INTAKE_PACKET_ID:
        raise CityOpsContractError("answer intake packet id drift")
    if packet.get("packet_status") != AAS_OPERATOR_ANSWER_INTAKE_PACKET_STATUS:
        raise CityOpsContractError("answer intake packet status drift")
    source = packet.get("source_gate", {})
    if source.get("file") != AAS_OPERATOR_ANSWER_RECEIPT_GATE_FILENAME:
        raise CityOpsContractError("answer intake packet source file drift")
    if source.get("digest_sha256") != _stable_digest(source_gate):
        raise CityOpsContractError("answer intake packet source digest drift")

    firewall = packet.get("dream_priority_firewall", {})
    if firewall.get("first_read") != "DREAM-PRIORITIES.md":
        raise CityOpsContractError("answer intake packet dream priority source drift")
    for key in [
        "autojob_work_allowed",
        "frontier_academy_work_allowed",
        "kk_v2_work_allowed",
        "karmacadabra_v2_work_allowed",
    ]:
        if firewall.get(key) is not False:
            raise CityOpsContractError(f"answer intake packet allowed stopped project: {key}")

    contract = packet.get("one_answer_intake_contract", {})
    if contract.get("future_receipt_schema") != FUTURE_RECEIPT_SCHEMA:
        raise CityOpsContractError("answer intake packet future schema drift")
    if contract.get("one_answer_only") is not True:
        raise CityOpsContractError("answer intake packet one-answer contract missing")
    if contract.get("template_is_not_receipt") is not True:
        raise CityOpsContractError("answer intake packet template promoted to receipt")
    if contract.get("template_records_no_current_answer") is not True:
        raise CityOpsContractError("answer intake packet current answer drift")
    values = contract.get("allowed_operator_answer_values", [])
    if [item.get("value") for item in values] != ALLOWED_FUTURE_DECISIONS:
        raise CityOpsContractError("answer intake packet allowed values drift")
    for item in values:
        if item.get("selected_by_this_packet") is not False:
            raise CityOpsContractError("answer intake packet selected an answer")
        if item.get("approval_granted_by_this_packet") is not False:
            raise CityOpsContractError("answer intake packet granted approval")
        expected_gate = NEXT_REQUIRED_GATE_BY_VALUE[item["value"]]
        if item.get("next_required_gate_if_explicitly_chosen") != expected_gate:
            raise CityOpsContractError("answer intake packet next-gate drift")
    if contract.get("future_receipt_required_fields") != RECEIPT_REQUIRED_FIELDS:
        raise CityOpsContractError("answer intake packet required fields drift")
    if sorted(DISALLOWED_OPERATOR_REFERENCE_PATTERNS.keys()) != contract.get(
        "operator_reference_rules", {}
    ).get("disallowed_material"):
        raise CityOpsContractError("answer intake packet operator reference rules drift")

    readiness = packet.get("readiness", {})
    for key, expected in INTAKE_PACKET_FALSE_FLAGS.items():
        if readiness.get(key) is not expected:
            raise CityOpsContractError(f"answer intake packet promoted readiness {key}")

    safe = set(packet.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(packet.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_OPERATOR_ANSWER_INTAKE_PACKET_SAFE_CLAIM not in safe:
        raise CityOpsContractError("answer intake packet safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"answer intake packet forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(INTAKE_PACKET_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"answer intake packet missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(f"answer intake packet claim overlap: {sorted(overlap)}")
    if packet.get("still_blocked_claims") != packet.get("claim_boundaries", {}).get(
        "do_not_claim_yet"
    ):
        raise CityOpsContractError("answer intake packet blocked claims drift")


def write_aas_operator_answer_intake_packet(
    *, artifact_dir: str | Path | None = None
) -> Path:
    target_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    packet = build_aas_operator_answer_intake_packet(artifact_dir=target_dir)
    target_path = target_dir / AAS_OPERATOR_ANSWER_INTAKE_PACKET_FILENAME
    target_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path


def load_aas_operator_answer_intake_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    path = source_dir / AAS_OPERATOR_ANSWER_INTAKE_PACKET_FILENAME
    packet = json.loads(path.read_text(encoding="utf-8"))
    source_gate = load_aas_operator_answer_receipt_gate(artifact_dir=source_dir)
    _assert_aas_operator_answer_intake_packet(packet, source_gate=source_gate)
    return packet
