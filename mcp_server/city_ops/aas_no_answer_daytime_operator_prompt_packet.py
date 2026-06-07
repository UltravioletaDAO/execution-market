"""Internal/admin AAS no-answer daytime operator prompt packet.

This slice consumes the AAS concept-gap implementation roadmap and turns the
current no-answer posture into one compact, reviewable daytime prompt packet.
It is deliberately not an operator answer, approval record, answer receipt,
customer/worker/public copy, route, queue, dispatch surface, runtime movement,
reputation action, payment verification, or stopped-project integration.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .aas_concept_gap_implementation_roadmap import (
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA,
    AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS,
    ROADMAP_BLOCKED_CLAIMS,
    load_aas_concept_gap_implementation_roadmap,
)
from .compliance_desk_fixture_review_gate import ARTIFACT_DIR
from .contracts import CityOpsContractError

AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SCHEMA = (
    "city_ops.aas_no_answer_daytime_operator_prompt_packet.v1"
)
AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME = (
    "aas_no_answer_daytime_operator_prompt_packet.json"
)
AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM = (
    "internal_admin_aas_no_answer_daytime_operator_prompt_packet_landed"
)
AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_ID = (
    "execution_market.aas.no_answer_daytime_operator_prompt_packet.2026_06_07_0200"
)
AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_STATUS = (
    "internal_admin_prompt_packet_only_no_answer_no_approval_no_delivery_or_runtime_movement"
)

PROMPT_ALLOWED_ANSWER_VALUES = [
    "hold_all_aas_lanes",
    "answer_retail_reality_boundary_only",
    "answer_document_handoff_boundary_only",
    "answer_compliance_desk_delivery_path_only",
    "answer_field_asset_ops_boundary_only",
    "answer_event_readiness_boundary_only",
    "answer_incident_verification_boundary_only",
    "answer_local_data_collection_boundary_only",
    "answer_property_ops_boundary_only",
    "answer_runtime_memory_read_only_prerequisite_inventory_only",
    "answer_runtime_memory_later_live_parity_attempt_only",
    "pause_aas_proof_layering",
]

ANSWER_VALUE_TO_FAMILY = {
    "answer_retail_reality_boundary_only": "retail_reality",
    "answer_document_handoff_boundary_only": "document_handoff",
    "answer_compliance_desk_delivery_path_only": "compliance_desk",
    "answer_field_asset_ops_boundary_only": "field_asset_ops",
    "answer_event_readiness_boundary_only": "event_readiness",
    "answer_incident_verification_boundary_only": "incident_verification",
    "answer_local_data_collection_boundary_only": "local_data_collection",
    "answer_property_ops_boundary_only": "property_ops",
    "answer_runtime_memory_read_only_prerequisite_inventory_only": "system_integration_runtime_memory",
    "answer_runtime_memory_later_live_parity_attempt_only": "system_integration_runtime_memory",
}

FALSE_FLAGS = {
    "packet_records_operator_answer": False,
    "packet_records_operator_approval": False,
    "packet_creates_answer_receipt": False,
    "packet_selects_future_answer": False,
    "packet_approves_product_exposure": False,
    "packet_creates_customer_public_or_worker_copy": False,
    "packet_creates_catalog_pricing_quote_route_or_queue": False,
    "packet_launches_dispatch_or_worker_instruction": False,
    "packet_emits_reputation_or_worker_skill_dna": False,
    "packet_reverifies_payment_or_production": False,
    "packet_mutates_runtime_acontext_irc_or_session_manager": False,
    "packet_exposes_exact_gps_raw_metadata_private_context_or_pii": False,
    "packet_grants_domain_legal_regulatory_safety_repair_or_sla_authority": False,
    "packet_publishes_worker_copyable_doctrine": False,
    "packet_integrates_or_expands_stopped_projects": False,
}

REQUIRED_PROMPT_FIELDS = [
    "one_allowed_answer_value_from_packet_only",
    "source_artifact_and_digest",
    "selected_family_or_hold_value",
    "explicit_boundary_text",
    "explicit_exclusions_for_delivery_runtime_dispatch_reputation_payment_private_context_and_stopped_projects",
    "answer_receipt_required_before_any_follow_on_gate",
]

PROMPT_BLOCKED_CLAIMS = [
    *ROADMAP_BLOCKED_CLAIMS,
    "no_answer_prompt_packet_records_operator_answer",
    "no_answer_prompt_packet_records_operator_approval",
    "no_answer_prompt_packet_creates_answer_receipt",
    "no_answer_prompt_packet_selects_future_answer",
    "no_answer_prompt_packet_treats_prompt_as_permission",
    "no_answer_prompt_packet_approves_customer_public_or_worker_copy",
    "no_answer_prompt_packet_approves_catalog_pricing_quote_route_queue_or_dispatch",
    "no_answer_prompt_packet_approves_worker_instruction_or_worker_copyable_doctrine",
    "no_answer_prompt_packet_attaches_reputation_worker_skill_dna_or_portable_credential",
    "no_answer_prompt_packet_reverifies_payment_or_production",
    "no_answer_prompt_packet_mutates_runtime_acontext_irc_or_session_manager",
    "no_answer_prompt_packet_releases_exact_gps_raw_metadata_private_context_or_pii",
    "no_answer_prompt_packet_grants_domain_legal_regulatory_safety_repair_or_sla_authority",
    "no_answer_prompt_packet_integrates_or_expands_stopped_projects",
]

FORBIDDEN_SAFE_CLAIMS = set(PROMPT_BLOCKED_CLAIMS) | {
    "operator_answer_recorded",
    "operator_approval_recorded",
    "answer_receipt_created",
    "customer_copy_ready",
    "public_catalog_ready",
    "pricing_ready",
    "route_ready",
    "queue_ready",
    "dispatch_ready",
    "worker_instruction_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "runtime_parity_proven",
    "live_acontext_ready",
    "gps_release_ready",
    "private_context_release_ready",
    "pii_release_ready",
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


def _assert_source_roadmap(roadmap: dict[str, Any]) -> None:
    if roadmap.get("schema") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SCHEMA:
        raise CityOpsContractError("AAS no-answer prompt source schema drift")
    if roadmap.get("roadmap_status") != AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_STATUS:
        raise CityOpsContractError("AAS no-answer prompt source status drift")
    safe = set(roadmap.get("claim_boundaries", {}).get("safe_to_claim", []))
    if AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS no-answer prompt source safe claim missing")
    blocked = set(roadmap.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    missing = set(ROADMAP_BLOCKED_CLAIMS) - blocked
    if missing:
        raise CityOpsContractError(
            f"AAS no-answer prompt source missing blocked claims: {sorted(missing)}"
        )
    state = roadmap.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS no-answer prompt source promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS no-answer prompt source selected decision")
    rows = roadmap.get("roadmap_rows", [])
    if len(rows) != 9:
        raise CityOpsContractError("AAS no-answer prompt source row count drift")
    ranks = [row.get("planning_sequence_rank") for row in rows]
    if ranks != list(range(1, 10)):
        raise CityOpsContractError("AAS no-answer prompt source rank sequence drift")
    if not all(row.get("still_blocked") is True for row in rows):
        raise CityOpsContractError("AAS no-answer prompt source row unblocked")
    runtime_rows = [
        row for row in rows if row.get("aas_family") == "system_integration_runtime_memory"
    ]
    if len(runtime_rows) != 1:
        raise CityOpsContractError("AAS no-answer prompt runtime row missing")
    if runtime_rows[0].get("next_allowed_without_human_answer") != "pause_aas_proof_layering":
        raise CityOpsContractError("AAS no-answer prompt runtime no-answer posture drift")
    firewall = roadmap.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS no-answer prompt source allowed {key}")


def _build_answer_choices(roadmap: dict[str, Any]) -> list[dict[str, Any]]:
    rows_by_family = {row["aas_family"]: row for row in roadmap["roadmap_rows"]}
    choices: list[dict[str, Any]] = [
        {
            "answer_value": "hold_all_aas_lanes",
            "selected_family": None,
            "allowed_follow_on_before_answer_receipt": "none",
            "meaning": "Hold all AAS proof layering and record no new approval, delivery, runtime, dispatch, reputation, or payment movement.",
            "required_next_gate": "none_until_separate_explicit_operator_answer",
        }
    ]
    for answer_value in PROMPT_ALLOWED_ANSWER_VALUES[1:-1]:
        family = ANSWER_VALUE_TO_FAMILY[answer_value]
        row = rows_by_family[family]
        choices.append(
            {
                "answer_value": answer_value,
                "selected_family": family,
                "source_row_rank": row["planning_sequence_rank"],
                "source_backed_current_state": row["source_backed_current_state"],
                "boundary_prompt_hint": row["roadmap_next_planning_slice"],
                "allowed_follow_on_before_answer_receipt": "none",
                "required_next_gate": row[
                    "required_gate_before_any_delivery_or_runtime_movement"
                ],
                "still_blocked_until_answer_receipt": True,
            }
        )
    choices.append(
        {
            "answer_value": "pause_aas_proof_layering",
            "selected_family": None,
            "allowed_follow_on_before_answer_receipt": "none",
            "meaning": "Pause AAS proof layering; preserve existing artifacts and do not create new answer, delivery, runtime, dispatch, reputation, or payment authority.",
            "required_next_gate": "none_until_separate_explicit_operator_answer",
        }
    )
    return choices


def build_aas_no_answer_daytime_operator_prompt_packet(
    *,
    artifact_dir: str | Path | None = None,
    source_roadmap: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a conservative no-answer daytime prompt packet for AAS review."""

    source_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    roadmap = source_roadmap or load_aas_concept_gap_implementation_roadmap(
        artifact_dir=source_dir
    )
    _assert_source_roadmap(roadmap)

    packet = {
        "schema": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SCHEMA,
        "packet_id": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_ID,
        "packet_status": AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_STATUS,
        "source_roadmap": {
            "file": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_FILENAME,
            "schema": roadmap["schema"],
            "roadmap_id": roadmap["roadmap_id"],
            "safe_claim": AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
            "digest_sha256": _stable_digest(roadmap),
            "consumed_rows": len(roadmap["roadmap_rows"]),
        },
        "governing_priority": {
            "source": "/Users/clawdbot/clawd/DREAM-PRIORITIES.md",
            "allowed_lane": "Execution Market AAS / City-as-a-Service internal/admin prompt planning",
            "stopped_project_firewall": {
                "autojob_work_allowed": False,
                "frontier_academy_work_allowed": False,
                "kk_v2_work_allowed": False,
                "karmacadabra_v2_work_allowed": False,
            },
        },
        "current_operator_state": {
            "explicit_operator_answer_available": False,
            "operator_approval_recorded": False,
            "answer_receipt_created": False,
            "selected_decision": None,
            "recommended_no_human_posture": "ask_for_one_explicit_operator_answer_or_hold_all_lanes",
        },
        "readiness": dict(FALSE_FLAGS),
        "daytime_prompt_packet": {
            "allowed_use": "internal_admin_daytime_prompt_packet_only",
            "prompt_goal": "obtain_one_explicit_operator_answer_or_hold_without_creating_permission",
            "required_prompt_fields": list(REQUIRED_PROMPT_FIELDS),
            "allowed_answer_values": list(PROMPT_ALLOWED_ANSWER_VALUES),
            "answer_choices": _build_answer_choices(roadmap),
            "recommended_prompt_text": (
                "Choose exactly one AAS answer value from this packet: hold_all_aas_lanes, "
                "one named family boundary answer, one runtime-memory mode, or pause_aas_proof_layering. "
                "Your reply creates only an answer candidate; a separate answer receipt must be written "
                "before any customer, worker, catalog, route, queue, dispatch, reputation, payment, "
                "runtime, private-context, or stopped-project movement."
            ),
            "next_gate_after_any_human_answer": "write_separate_answer_receipt_then_run_specific_gate",
            "still_blocked": True,
        },
        "sequence_rules": [
            "Use this packet to ask for exactly one explicit operator answer or a hold value; do not infer approval from silence.",
            "Treat every answer value as inert until a separate answer receipt validates the source artifact, digest, selected boundary, and exclusions.",
            "Do not create customer, public, worker, catalog, pricing, quote, route, queue, dispatch, reputation, payment, or runtime movement from this packet.",
            "Do not expose exact GPS, raw metadata, private context, PII, or worker-copyable doctrine.",
            "Keep AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 out of the active dream workstream.",
        ],
        "claim_boundaries": {
            "safe_to_claim": [
                AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_SAFE_CLAIM,
                AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM,
            ],
            "do_not_claim_yet": _dedupe(PROMPT_BLOCKED_CLAIMS),
        },
        "packet_digest_sha256": "",
    }
    packet["packet_digest_sha256"] = _stable_digest(
        {k: v for k, v in packet.items() if k != "packet_digest_sha256"}
    )
    _assert_prompt_packet_conservative(packet, source_roadmap=roadmap)
    return packet


def write_aas_no_answer_daytime_operator_prompt_packet(
    *, artifact_dir: str | Path | None = None
) -> Path:
    """Persist the no-answer daytime operator prompt packet."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    packet = build_aas_no_answer_daytime_operator_prompt_packet(artifact_dir=base_dir)
    path = base_dir / AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_aas_no_answer_daytime_operator_prompt_packet(
    *, artifact_dir: str | Path | None = None
) -> dict[str, Any]:
    """Load and validate the persisted no-answer daytime operator prompt packet."""

    base_dir = Path(artifact_dir) if artifact_dir is not None else ARTIFACT_DIR
    packet = json.loads(
        (base_dir / AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    source_roadmap = load_aas_concept_gap_implementation_roadmap(artifact_dir=base_dir)
    _assert_prompt_packet_conservative(packet, source_roadmap=source_roadmap)
    return packet


def _assert_prompt_packet_conservative(
    packet: dict[str, Any], *, source_roadmap: dict[str, Any]
) -> None:
    _assert_source_roadmap(source_roadmap)
    if packet.get("schema") != AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SCHEMA:
        raise CityOpsContractError("AAS no-answer prompt packet schema drift")
    if packet.get("packet_id") != AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_ID:
        raise CityOpsContractError("AAS no-answer prompt packet id drift")
    if packet.get("packet_status") != AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_STATUS:
        raise CityOpsContractError("AAS no-answer prompt packet status drift")
    source = packet.get("source_roadmap", {})
    if source.get("digest_sha256") != _stable_digest(source_roadmap):
        raise CityOpsContractError("AAS no-answer prompt packet source digest drift")
    if source.get("consumed_rows") != 9:
        raise CityOpsContractError("AAS no-answer prompt packet consumed row count drift")

    state = packet.get("current_operator_state", {})
    for key in [
        "explicit_operator_answer_available",
        "operator_approval_recorded",
        "answer_receipt_created",
    ]:
        if state.get(key) is not False:
            raise CityOpsContractError(f"AAS no-answer prompt packet promoted {key}")
    if state.get("selected_decision") is not None:
        raise CityOpsContractError("AAS no-answer prompt packet selected future decision")

    for key, expected in FALSE_FLAGS.items():
        if packet.get("readiness", {}).get(key) is not expected:
            raise CityOpsContractError(f"AAS no-answer prompt packet readiness promoted {key}")

    prompt = packet.get("daytime_prompt_packet", {})
    if prompt.get("allowed_use") != "internal_admin_daytime_prompt_packet_only":
        raise CityOpsContractError("AAS no-answer prompt packet use drift")
    if prompt.get("prompt_goal") != "obtain_one_explicit_operator_answer_or_hold_without_creating_permission":
        raise CityOpsContractError("AAS no-answer prompt packet goal drift")
    if prompt.get("next_gate_after_any_human_answer") != "write_separate_answer_receipt_then_run_specific_gate":
        raise CityOpsContractError("AAS no-answer prompt packet next gate drift")
    if prompt.get("still_blocked") is not True:
        raise CityOpsContractError("AAS no-answer prompt packet unblocked")
    if set(REQUIRED_PROMPT_FIELDS) - set(prompt.get("required_prompt_fields", [])):
        raise CityOpsContractError("AAS no-answer prompt packet missing prompt fields")
    choices = prompt.get("answer_choices", [])
    values = [choice.get("answer_value") for choice in choices]
    if values != PROMPT_ALLOWED_ANSWER_VALUES:
        raise CityOpsContractError("AAS no-answer prompt packet answer values drift")
    for choice in choices:
        if choice.get("allowed_follow_on_before_answer_receipt") != "none":
            raise CityOpsContractError("AAS no-answer prompt packet allowed follow-on too early")
        if choice.get("answer_value", "").startswith("answer_") and choice.get(
            "still_blocked_until_answer_receipt"
        ) is not True:
            raise CityOpsContractError("AAS no-answer prompt packet answer choice unblocked")

    safe = set(packet.get("claim_boundaries", {}).get("safe_to_claim", []))
    blocked = set(packet.get("claim_boundaries", {}).get("do_not_claim_yet", []))
    if AAS_NO_ANSWER_DAYTIME_OPERATOR_PROMPT_PACKET_SAFE_CLAIM not in safe:
        raise CityOpsContractError("AAS no-answer prompt packet safe claim missing")
    forbidden_safe = safe & FORBIDDEN_SAFE_CLAIMS
    if forbidden_safe:
        raise CityOpsContractError(
            f"AAS no-answer prompt packet forbidden safe claims: {sorted(forbidden_safe)}"
        )
    missing_blocked = set(PROMPT_BLOCKED_CLAIMS) - blocked
    if missing_blocked:
        raise CityOpsContractError(
            f"AAS no-answer prompt packet missing blocked claims: {sorted(missing_blocked)}"
        )
    overlap = safe & blocked
    if overlap:
        raise CityOpsContractError(
            f"AAS no-answer prompt packet claim overlap: {sorted(overlap)}"
        )

    firewall = packet.get("governing_priority", {}).get("stopped_project_firewall", {})
    for key, value in firewall.items():
        if value is not False:
            raise CityOpsContractError(f"AAS no-answer prompt packet allowed {key}")
